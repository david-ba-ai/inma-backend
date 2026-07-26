import sqlglot
from opencage.geocoder import OpenCageGeocode
import os
import math
import sqlite3
import re
from sqlglot import exp
from typing import List, Dict
import random
from langchain_core.messages import AIMessage
from src.data_generation.json_view_data_generation import search_in_json_by_id
from src.config import columns_dir
import json

# Campos requeridos para ejecutar una consulta SQL
required_fields = ["Tipo", "Operacion", "NumDormitorios", "Precio", "Barrio"]
localization_fields = ["Municipio", "Poblacion"]

fields = []
history_fields = []

with open(columns_dir, "r", encoding="utf-8") as file:
        data = json.load(file)
        json_columns = data.get("api_columns", []) + data.get("enrichment_columns", [])
        fields = [col.get("name") for col in json_columns  if col.get("search")]
        fields.append("Id")
        history_fields = [col.get("name") for col in json_columns if col.get("presentation")]


# ------ GENERACIÓN DE CONSULTA SQL UTILIZANDO ID ------
def generate_sql_ids(lista_ids: List[int]) -> str:
    """ Esta función se ejecuta en el PASO 1 para extraer información de los inmuebles ya buscados 
    """
    if not lista_ids:
        return "SELECT * FROM inmuebles WHERE 1=0;"  # Retorna una consulta que no devuelve resultados
    
    ids_str = ", ".join(map(str, lista_ids))
    return f"SELECT * FROM inmuebles WHERE Id IN ({ids_str});"


# ------ CONVERSIÓN DE RESULTADOS DE SQLITE A DICCIONARIO ------
def parse_db_answer(list_values: list[sqlite3.Row]) -> Dict[int, Dict]:
    """ Esta función se ejecuta en el PASO 1 para extraer dar estructura a los resultados de la base de datos, indexados por ID.
        Devuelve todos los campos de búsqueda, indexados por ID
    """
    if not list_values:
        return {}
    
    data_dict = {row["Id"]: dict(row) for row in list_values}

    return data_dict


# ------ PARSEADO DE LOS RESULTADOS DE LA BASE DA DATOS, FILTRANDO POR COLUMNAS DE PRESENTACIÓN ------
def filter_presentation_fields(parsed_results: Dict[int, Dict]) -> Dict[int, Dict]:
    """Esta función se ejecuta en el PASO 1 para filtrar los campos de interes en la presentacion.
       Devuelve solo los campos de presentacion, indexados por ID
    """
    filtered_results = {}

    for id, values in parsed_results.items():
        filtered_results[id] = {field: value for field, value in values.items() if field in history_fields}

    return filtered_results

# ------ DATOS PARA LA PRESENTACIÓN DE UN INMUEBLE ESPECÍFICO ------
def specific_presentation_dict(inm_data: Dict[str, str], inm_id: int) -> tuple[Dict, str, str, List[str], tuple[float, float]]:
    """ Esta función se ejecuta en el PASO 2 para contestar preguntar sobre inmuebles ya presentados y en el paso 3 para presentar un nuevo inmueble 
        inm_data solo contiene los campos específicos de presentación
    """
    view_result = search_in_json_by_id(inm_id) # Extraemos columnas adicionales del JSON utilizando el Id
    
    url_externa = inm_data.pop("URLExterna", None)
    main_photo = view_result.get("Foto", None)
    public_observations = view_result.get("Observaciones_Publicas", None)
    inm_data["Observaciones_Publicas"] = public_observations
    photo_urls = view_result.get("array_url_fotos", "[]")
    lon_inm = float(view_result.get("Longitud", None))
    lat_inm = float(view_result.get("Latitud", None))

    return inm_data, url_externa, main_photo, photo_urls, (lon_inm, lat_inm)


# ------ EXTRAE LOS CAMPOS DENTRO DE LA CLÁUSULA WHERE DE UNA CONSULTA SQL ------
def extract_columns_from_sql(sql_query: str) -> List[str]:
    """ Se ejecuta dentro de la función check_fields_in_query() y en extract_column_by_priority()
    """
    parsed = sqlglot.parse_one(sql_query)
    
    # Lista para almacenar las columnas encontradas
    columns = set()
    
    # Función recursiva para recorrer el árbol sintáctico
    def traverse(node):
        if isinstance(node, exp.Column):
            # Si el nodo es una columna, añadir su nombre
            columns.add(node.name)
        elif isinstance(node, exp.Expression):
            # Si el nodo es una expresión, recorrer sus hijos
            for child in node.args.values():
                if isinstance(child, list):  # Si es una lista, iteramos sobre ella
                    for sub_child in child:
                        traverse(sub_child)
                else:
                    traverse(child)

    # Empezar el recorrido desde la cláusula WHERE
    where_clause = parsed.find(exp.Where)
    if where_clause:
        traverse(where_clause)

    return list(columns)


# ------ CAMPOS REQUERIDOS PARA LA EJECUTAR UNA BÚSQUEDA EN BASE DE DATOS ------
def check_fields_in_query(sql_query: str, inm_localization: tuple) -> List[str]:
    """ Se ejecuta en el PASO 4, tras haber generado una consulta SQL y haber sido esta modificada. 
    """    
    extracted_columns: List[str] = extract_columns_from_sql(sql_query)

    # Determinar los campos obligatorios que faltan
    missing_fields = [field for field in required_fields if field not in extracted_columns]

    # Verificar si se debe agregar "Poblacion"
    if not any(field in extracted_columns for field in localization_fields):
        missing_fields.append("Poblacion")

    if "Municipio" in extracted_columns and "Barrio" in missing_fields:
        missing_fields.remove("Barrio")

    if "EsCentro" in extracted_columns and "Barrio" in missing_fields:
        missing_fields.remove("Barrio")

    if inm_localization and "Barrio" in missing_fields:
        missing_fields.remove("Barrio")

    if "Barrio" in missing_fields and len(missing_fields)>1:
        missing_fields.remove("Barrio")

    return missing_fields


# ------ DATOS PARA LA PRESENTACIÓN DE VARIOS INMUEBLE LOCALIZADOS ------
def general_presentation_dict(list_values: tuple) -> Dict[int, Dict]:
    """ Esta función se ejecuta en el PASO 7, para mostrar los resultados obtenidos tras la consulta SQL ejecutada 
    """

    parsed_results: Dict[int, Dict] = parse_db_answer(list_values)

    filtered_results: Dict[int, Dict] = filter_presentation_fields(parsed_results)

    list_data = {}

    for id, values in filtered_results.items():
        view_result = search_in_json_by_id(id) # Extraemos columnas adicionales del JSON utilizando el Id
        url: str = view_result.get("URLExterna", None)
        url_media: str = view_result.get("Foto", None)

        property_type = values.get("Tipo")

        values["Superficie"] = values["Metros_Construidos"]

        # Si el inmueble es un "Piso" y no tiene "Metros_Construidos", asignamos "Metros_Utiles"
        if property_type == "Piso" and not values.get("Metros_Construidos"):
            values["Superficie"] = values.get("Metros_Utiles")

        # Si el inmueble es una "Fincas y solares", usamos "Metros_Parcela"
        if property_type == "Fincas y solares":
            values["Superficie"] = values.get("Metros_Parcela")

        list_data[id] = {
            "data_inm": values,
            "url": url,
            "url_media": url_media
        }

    return list_data


# ------RECLAMAR LOCALIZACIÓN PRECISA DEL INMUEBLE ------
def reclame_localization(missing_fields: List[str])-> bool:
    """ Se ejecuta en el PASO 5 para la demanda de campos faltantes y resulta en la generación de un mapa de localización.
    """
    return "Barrio" in missing_fields and len(missing_fields)==1


# ------ LOCALIZACIÓN DE COORDENADAS DE LA POBLACIÓN ------
def city_localization(query: str) -> tuple:
    """
    Esta función devuelve las coordenadas de la ciudad indicada en el campo 'Poblacion' de la consulta SQL. Se usa para posicionar el mapa interactivo.
    Se ejecuta en el PASO 5 para la demanda de campos faltantes.
    """
    def extract_like_value(sql_query, column_name) -> str:
        pattern = rf"{column_name}\s+LIKE\s+['\"](.*?)['\"]"
        match = re.search(pattern, sql_query, re.IGNORECASE)

        return match.group(1) if match else None
    
    query_city = extract_like_value(query, "Poblacion")
    query_city = query_city.strip("%")

    results = []

    try:
        OCG = OpenCageGeocode(os.getenv("OPENCAGE_KEY"))
        results = OCG.geocode(f"{query_city}, España")
        print(f"DEBUG: {results}")
    except Exception as e:
        pass

    if results:
        lat = results[0]['geometry']['lat']
        lon = results[0]['geometry']['lng']
    else:
        lat = "43.3618625"
        lon = "-5.8483581"

    return lat, lon


# ------ BÚSQUEDA CON FILTRO GEOESPACIAL ------
def add_geospatial_filter(sql_base: str, coordinates: tuple[float, float], radius: int = 800) -> str:
    """
    Esta función transforma la consulta SQL para que incorpore búsqueda geoespacial en función de una localización y un radio alrededor de esta.
    Se ejecuta en el PASO 3 tras la generación de la consulta SQL.
    """
     
    lat_c = float(coordinates[0])
    lon_c = float(coordinates[1])
    sql_base = sql_base.strip().rstrip(';')

    sql_base = remove_column_in_where(sql_base, "Barrio") # Eliminamos Barrio para que no haya interferencias
    
    # Conversión de grados a metros
    factor_lat = 111320  # Metros por grado de latitud
    factor_lon = 111320 * math.cos(math.radians(lat_c))  # Metros por grado de longitud en esta latitud

    # Expresión para el cálculo de la distancia en metros
    geo_filter = f"""
    ((Latitud - {lat_c}) * {factor_lat}) * ((Latitud - {lat_c}) * {factor_lat}) +
    ((Longitud - ({lon_c})) * {factor_lon}) * ((Longitud - ({lon_c})) * {factor_lon})
    <= ({radius} * {radius})
    """

    # Modificar la consulta agregando el filtro de distancia
    if "WHERE" in sql_base.upper():
        sql_modified = f"{sql_base} AND {geo_filter}"
    else:
        sql_modified = f"{sql_base} WHERE {geo_filter}"

    return sql_modified


# ------ EXTRACIÓN DE COLUMNA CON MAYOR PRIORIDAD PARA ELIMINACIÓN ------
def extract_column_by_priority(sql_query: str, priority: int) -> str:
    """
    Esta función devuelve la consulta SQL habiendo extraído una condición del WHERE, según su prioridad de exclusión.
    Valores más altos indican mayor probabilidad de eliminarla de la consulta.
    Se ejecuta en el PASO 5, en caso de que la ejecución de la consulta no haya dado resultados.
    """
    def columns_priority()-> List[Dict]:
        """Genera una lista de diccionarios para cada columna, indicando su tipo y su prioridad."""
        with open(columns_dir, "r", encoding="utf-8") as file:
            data = json.load(file)
            json_columns = data.get("api_columns", []) + data.get("enrichment_columns", [])

        json_columns_by_priority = []
        for col in json_columns:
            if col.get("search"): 
                col_name = col.get("name")
                col_type = col.get("type")
                col_priority = col.get("priority", 5)
                json_columns_by_priority.append({"name":col_name, "type": col_type, "priority": col_priority})
        
        return json_columns_by_priority
    
    def get_max_priority(columns: List[str], columns_by_priority: List[Dict]) -> int:
        """Extrae el valor de prioridad más alto de una lista de columnas"""
        priorities = [
            col.get("priority")
            for col in columns_by_priority
            if col["name"] in columns
        ]
        
        return max(priorities, default=0)
    
    # Extraemos las columnas ordenadas por prioridad
    columns_by_priority: List[Dict] = columns_priority()

    # Extraemos las columnas de WHERE de la consulta SQL
    sql_columns: List[str] = extract_columns_from_sql(sql_query)

    # Obtenemos el nivel máximo de prioridad de las columnas de la consulta SQL
    max_priority = get_max_priority(sql_columns, columns_by_priority)

    if max_priority>=priority:

        # Seleccionamos las columnas con la prioridad dada
        columns_by_this_priority: List[str] = [col["name"] for col in columns_by_priority if col["name"] in sql_columns and col["priority"] == max_priority]

        # Seleccionamos aleatoriamente una de las columnas
        random_column = random.choice(columns_by_this_priority) if columns_by_this_priority else None

        # Eliminamos la columna seleccionada de las condiciones WHERE de la consulta
        return random_column
    
    return sql_query


# ------ COMBINACIÓN DE CLÁUSULAS WHERE EN DOS CONSULTAS ------
def merge_sql_queries(new_query: str, last_query: str) -> str:
    """
    Función para fusionar dos consultas SQL combinando exclusivamente sus cláusulas WHERE y priorizando las condiciones de new_query.
    Se llama en el PASO 3, tras la generación de la consulta SQL.
    """

    # Parsear las consultas SQL con sqlglot
    new_expr = sqlglot.parse_one(new_query)
    last_expr = sqlglot.parse_one(last_query)

    # Extraer la cláusula WHERE de ambas consultas
    new_where = new_expr.find(exp.Where)
    last_where = last_expr.find(exp.Where)

    # Extraer condiciones de cada WHERE como diccionario {columna: condición}
    def extract_conditions(where_clause):
        conditions = {}
        if where_clause:
            for condition in where_clause.this.flatten():  # Extrae todas las condiciones
                if isinstance(condition, (exp.EQ, exp.LT, exp.LTE, exp.GT, exp.GTE, exp.Like, exp.Not, exp.In)):
                    column_name = condition.this.name if isinstance(condition.this, exp.Column) else None
                    if column_name:
                        conditions[column_name] = condition
        return conditions

    new_conditions = extract_conditions(new_where)
    last_conditions = extract_conditions(last_where)

    # Fusionar condiciones, priorizando las de new_query
    merged_conditions = {**last_conditions, **new_conditions}  # new_conditions sobrescribe last_conditions

    # Construir la nueva cláusula WHERE combinada
    if merged_conditions:
        combined_where = exp.and_(*merged_conditions.values())
        new_expr.set("where", exp.Where(this=combined_where))

    # Devolver la consulta SQL fusionada
    return new_expr.sql()


# ------ EXCLUSIÓN DE INMUEBLES YA BUSCADOS ------
def add_id_exclusion(sql_query: str, id_list: List[int]) -> str:
    """
    Función para excluir una lista de IDs en la consulta SQL.
    Se llama en el PASO 3, tras la generación de la consulta SQL.
    """

    if not id_list:
        return sql_query  # Si la lista está vacía, devolver la consulta sin cambios.

    # Parsear la consulta SQL
    expression = sqlglot.parse_one(sql_query)

    # Generar la condición de exclusión:
    exclusion_condition = exp.Not(
        this=exp.In(
            this=exp.Column(this="Id"),
            expressions=[exp.Literal.number(id_value) for id_value in id_list]
        )
    )

    # Extraer o crear la cláusula WHERE
    where_clause = expression.find(exp.Where)
    
    if where_clause:
        # Si ya existe una cláusula WHERE, agregamos la exclusión con AND
        new_where_condition = exp.And(this=where_clause.this, expression=exclusion_condition)
        where_clause.set("this", new_where_condition)
    else:
        # Si no hay WHERE, lo creamos con la exclusión
        expression.set("where", exp.Where(this=exclusion_condition))

    modified_sql = expression.sql()
    # Devolver la consulta SQL modificada
    return modified_sql

# ------ LIMPIEZA GENÉRICA DE LA CONSULTA SQL ------
def parsing_sql_query(raw_query: AIMessage) -> dict:
    """ 
    Función para limpiar la consulta SQL.
    Se llama al final de la cadena text2sql_chain() que genera la consulta SQL.
    """
    
    def remove_accents(text):
            table = str.maketrans("áéíóúÁÉÍÓÚ", "aeiouAEIOU")
            text_without_accents = text.translate(table)
            return text_without_accents
    try:
        if hasattr(raw_query, 'content'):
            raw_query = raw_query.content
        
        # Eliminamos saltos de línea
        cleaned_query = raw_query.replace("\n", " ").strip()

        # Remueve las comillas invertidas si están presentes
        cleaned_query = raw_query.strip().strip('```').strip()

        # Eliminamos la tilde en las vocales
        cleaned_query = remove_accents(cleaned_query)
        
        # Si las comillas invertidas están al principio y al final, quítalas
        if cleaned_query.startswith("sql"):
            cleaned_query = cleaned_query[3:].strip()

    except Exception as e:
        raise Exception(f"ERROR: Unexpected error cleaning SQL query: {e}")

    return cleaned_query

# ------ ENRIQUECIMIENTO DE LA CONSULTA SQL SEGÚN LA LÓGICA DE NEGOCIO ------
def modify_query(sql_query: str):
    """
    Modifica algunos elementos de la consulta para adaptarlos a la lógica del negocio.
    Se ejecuta en el PASO 3, justo después de generar la consulta original y guardar esta en el modelo de sesión.
    """
    sql_query = modify_query_operacion(sql_query)
    sql_query = modify_query_precio(sql_query)
    
    return sql_query
    

def modify_query_operacion(sql_query: str):
    """ 
    Añade una condicion WHERE en la columna 'Operacion' en función del precio.
    Se ejecuta en la función parsing_sql_query(), al final de la cadena text2sql_chain()
    """
    def get_column_value(expression, column_name):
        if isinstance(expression, (exp.And, exp.Or)):  # Si es una expresión compuesta
            return get_column_value(expression.left, column_name) or get_column_value(expression.right, column_name)
        elif isinstance(expression, (exp.EQ, exp.LT, exp.LTE, exp.GT, exp.GTE)):
            if isinstance(expression.this, exp.Column) and expression.this.name == column_name:
                return expression.expression.this
        return None
    
    if "Precio" in sql_query:
    
        expression = sqlglot.parse_one(sql_query)
        
        # Extraer la cláusula WHERE
        where = expression.find(exp.Where)

        # Buscar el valor de 'Precio'
        precio_value = get_column_value(where.this, "Precio")

        if precio_value is not None:
            precio_value = int(precio_value)  # Convertir a entero si es posible
            if precio_value > 5000:
                nueva_condicion = exp.EQ(
                    this=exp.Column(this=exp.Identifier(this="Operacion")),
                    expression=exp.Literal(this="Venta", is_string=True)
                )
            else:
                nueva_condicion = exp.EQ(
                    this=exp.Column(this=exp.Identifier(this="Operacion")),
                    expression=exp.Literal(this="Alquiler", is_string=True)
                )

            # Crear una nueva cláusula WHERE combinando la existente con la nueva condición
            nuevo_where = exp.Where(
                this=exp.And(this=where.this, expression=nueva_condicion)
            )

            # Reemplazar la cláusula WHERE en la expresión principal
            expression = expression.transform(lambda node: nuevo_where if isinstance(node, exp.Where) else node)

            sql_query_modificada = expression.sql()

            return sql_query_modificada
    else:
        return sql_query


def modify_query_precio(sql_query):
    """ 
    Modifica una condicion WHERE en la columna 'Precio' para ampliar el rango.
    Se ejecuta en la función parsing_sql_query(), al final de la cadena text2sql_chain()
    """

    if "Precio" in sql_query:
        expression = sqlglot.parse_one(sql_query)

        # Extraer la cláusula WHERE
        where = expression.find(exp.Where)

        def update_precio(expression):
            if isinstance(expression, (exp.And, exp.Or)):  # Si es una expresión compuesta
                expression.set("this", update_precio(expression.this))
                expression.set("expression", update_precio(expression.expression))
                return expression
            elif isinstance(expression, (exp.EQ, exp.LT, exp.LTE, exp.GT, exp.GTE)):  # Si es una comparación
                if isinstance(expression.this, exp.Column) and expression.this.name == "Precio":
                    original_value = float(expression.expression.this)  # Obtener valor numérico
                    if isinstance(expression, exp.EQ):  # Convertir en BETWEEN
                        lower_bound = original_value * 0.8
                        upper_bound = original_value * 1.2
                        return exp.Between(
                            this=exp.Column(this="Precio"),
                            low=exp.Literal.number(int(lower_bound)),
                            high=exp.Literal.number(int(upper_bound)),
                        )
                    elif isinstance(expression, exp.LTE):  # Ampliar al 120%
                        new_value = original_value * 1.2
                        return exp.LTE(
                            this=exp.Column(this="Precio"),
                            expression=exp.Literal.number(int(new_value)),
                        )
                    elif isinstance(expression, exp.GTE):  # Reducir al 80%
                        new_value = original_value * 0.8
                        return exp.GTE(
                            this=exp.Column(this="Precio"),
                            expression=exp.Literal.number(int(new_value)),
                        )
            return expression

        if where:
            where.set("this", update_precio(where.this))

        return expression.sql()
    else:
        return sql_query


def modify_sql_prioridadrk(sql_query):
    """ 
    Añade una cláusula para ordenar las filas por 'PrioridadRK'. Además limita el resultado a 4 filas.
    Se ejecuta en el PASO 3, justo después de generar la consulta original y guardar esta en el modelo de sesión.
    """
    sql_query = sql_query.rstrip(';')
    modified_query = sql_query.strip() + " ORDER BY PrioridadRK DESC, RANDOM() LIMIT 4;"
    return modified_query


# ------ ELIMINA CONDICIONES EN WHERE SEGÚN COLUMNA------
def remove_column_in_where(sql: str, columna: str) -> str:
    """
    Elimina de la consulta SQL la condición de la cláusula WHERE que incluya la columna especificada.
    Se asume que las condiciones están unidas por AND.
    """
    # Buscar la cláusula WHERE (asumiendo que es la última parte de la consulta)
    match = re.search(r'(?i)\bWHERE\b(.*)', sql)
    if not match:
        return sql  # No hay cláusula WHERE, se devuelve la consulta original
    
    # Separar la consulta en dos partes: antes del WHERE y la cláusula WHERE
    inicio_where = match.start(0)  # posición donde inicia 'WHERE'
    where_keyword = match.group(0)[:match.group(0).upper().find("WHERE")+5]  # extrae "WHERE"
    where_clause = match.group(1).strip()  # extrae el contenido posterior a WHERE
    
    # Dividir las condiciones suponiendo que están separadas por AND
    condiciones = re.split(r'(?i)\s+AND\s+', where_clause)
    
    # Filtrar las condiciones que no contienen la columna a eliminar
    condiciones_filtradas = []
    patron_columna = re.compile(r'(?i)\b' + re.escape(columna) + r'\b')
    for cond in condiciones:
        if not patron_columna.search(cond):
            condiciones_filtradas.append(cond.strip())
    
    # Reconstruir la consulta
    # Tomar la parte de la consulta antes de la cláusula WHERE
    consulta_base = sql[:inicio_where].strip()
    
    if condiciones_filtradas:
        nueva_where = "WHERE " + " AND ".join(condiciones_filtradas)
        nueva_consulta = consulta_base + " " + nueva_where
    else:
        # Si no quedan condiciones, se elimina por completo la cláusula WHERE
        nueva_consulta = consulta_base
    
    # Mantener posible punto y coma final si lo hubiera
    if sql.strip()[-1] == ';' and nueva_consulta[-1] != ';':
        nueva_consulta += ';'
    
    return nueva_consulta




