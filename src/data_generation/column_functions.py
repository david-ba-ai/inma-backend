import pandas as pd
from typing import Dict, List
import numpy as np
import re
import math
import logging

#-------------------------------------------------------------------------------------------------------------------
logger = logging.getLogger(__name__)

#------CLEANER FUNCTIONS------

def integrating_localization_data(original_df: pd.DataFrame, geocode_df: pd.DataFrame) -> pd.DataFrame:
    """
    Esta función integra la información obtenida de la geocodificación inversa para estandarizar los datos de localización de los inmuebles.
     Ambos deben tener el mismo índice.
    :param original_df (pd.DataFrame): DataFrame original con los datos de los inmuebles
    :param geocode_df (pd.DataFrame): DataFrame original con los datos de los inmuebles
    :return (pd.DataFrame): DataFrame ya modificado
    """

    # Poblacion
    original_df.loc[original_df["Poblacion"].isna() | original_df["Poblacion"].eq("") | original_df["Poblacion"].str.isupper() & original_df["Municipio"].str.isupper()==False, "Poblacion"] = original_df["Municipio"]
    original_df.loc[original_df["Poblacion"].isna() & geocode_df["city"].notna(), "Poblacion"] = geocode_df["city"]
    original_df.loc[geocode_df["city"].isna() & geocode_df["town"].notna(), "Poblacion"] = geocode_df["town"]
    original_df.loc[geocode_df["city"].isna() & geocode_df["town"].isna() & geocode_df["village"].notna(), "Poblacion"] = geocode_df["village"]
    original_df.loc[geocode_df["city"].isna() & geocode_df["town"].isna() & geocode_df["village"].isna() & geocode_df["hamlet"].notna(), "Poblacion"] = geocode_df["hamlet"]

    #Zona
    original_df.loc[geocode_df["suburb"].notna(), "Zona"] = geocode_df["suburb"]

    #Código postal
    original_df.loc[original_df["CP"].isna() | (original_df["CP"] == 0), "CP"] = geocode_df["postcode"]

    #Direccion
    original_df.loc[geocode_df["road"]!= "unnamed road", "Direccion"] = geocode_df["road"]

    #Urbanización
    original_df["Urbanizacion"] = geocode_df["neighbourhood"]
    original_df.loc[geocode_df["neighbourhood"].isna(), "Urbanizacion"] = geocode_df["hamlet"]

    #Urbanización
    original_df["Carretera"] = geocode_df["road_reference"]
    original_df.loc[geocode_df["road_reference"].notna(), "Carretera"] = geocode_df["road_reference"]
    
    return original_df


def data_type_cleaning(df: pd.DataFrame, data_columns: Dict[str,str]) -> pd.DataFrame:
    """
    Función para ajustar los tipos de valores del DataFrame según las descripciones de las columnas.
    :param df (pd.DataFrame): DataFrame donde se va a producir el ajuste.
    :param data_columns (Dict[str,str]): Diccionario que almacena las características de las columnas.
    :returns (pd.DataFrame): DataFrame original ya ajustado.
    """
    pd.set_option('future.no_silent_downcasting', True)

    api_columns = data_columns.get("api_columns", [])
    
    for col_name in df.columns:
        col_type = next((col["type"] for col in api_columns if col.get("api_name", col.get("name")) == col_name), None)
        try:
            if col_type == "INTEGER":
                df[col_name] = pd.to_numeric(df[col_name], errors="coerce").fillna(0).astype(np.int64)
                    
            elif col_type in ["TEXT", "CHAR", "ENUM", "VARCHAR"]:
                df[col_name] = df[col_name].astype("string")
                    
            elif col_type == "REAL":
                df[col_name] = pd.to_numeric(df[col_name], errors="coerce").astype(np.float64)
                    
            elif col_type == "BOOLEAN":
                valid_values = {"no": False, "None": False, "none": False, 0: False, 1: True, "si": True}
                df[col_name] = df[col_name].replace(valid_values, regex=True)
                    
            else:
                print(f"Tipo de dato '{col_type}' no reconocido para la columna {col_name}.")
        except:
            print(f"La conversión no ha podido llevarse a cabo en la columna {col_name}")

    return df


def replace_values(df: pd.DataFrame) -> pd.DataFrame:
    """
    Función para estandarizar algunos valores de texto.
    :param df (pd.DataFrame): DataFrame donde se va a producir el ajuste.
    :returns (pd.DataFrame): DataFrame original ya ajustado.
    """
    pd.set_option('future.no_silent_downcasting', True)

    def replace_adress(texto):
        if texto is None or pd.isna(texto):
            return ""  # Retornar cadena vacía para valores nulos o NaN
        
        if not isinstance(texto, str):
            texto = str(texto)

        # Normalizar el texto según las reglas iniciales
        texto = re.sub(r'^(cm|Cm)', 'Camino', texto, flags=re.IGNORECASE)
        texto = re.sub(r'^(av)\s', 'Avenida ', texto, flags=re.IGNORECASE)
        texto = re.sub(r'^(avd)', 'Avenida', texto, flags=re.IGNORECASE)
        texto = re.sub(r'^(lg)', 'Lugar', texto, flags=re.IGNORECASE)
        texto = re.sub(r'^(Pz|pz)', 'Plaza', texto, flags=re.IGNORECASE)

        # Extraer desde "Calle" hasta el final o hasta el primer "/"
        if "Cai" in texto and "Calle" in texto:
            match = re.search(r'Calle.*?(?=/|$)', texto)
            if match:
                texto = match.group(0).strip()

        texto = re.sub(r'^(cl|cai|cl/|c/)', 'Calle', texto, flags=re.IGNORECASE)
        texto = re.sub(r'^(c)\s', 'Calle ', texto, flags=re.IGNORECASE)

        return texto
    
    def replace_windows(row):
        if row['CheckVentanasAluminio']:
            return 'Aluminio'
        elif row['CheckVentanasClimalit']:
            return 'Climalit'
        elif row['CheckVentanasMadera']:
            return 'Madera'
        elif row['CheckVentanasPVC']:
            return 'PVC'
        else:
            return None
    
    # Aplicamos modificaciones en la columna de 'Direccion' para estandarizar los valores
    df['Direccion'] = df['Direccion'].apply(replace_adress)

    # Combinamos las columnas booleanas de tipos de ventanas en una
    df['TipoVentana'] = df.apply(replace_windows, axis=1)
    df = df.drop(columns=['CheckVentanasAluminio', 'CheckVentanasClimalit', 'CheckVentanasMadera', 'CheckVentanasPVC'])

    # Combinamos el número de aseos y baños en una sola columna
    df["Aseos"] = df["Aseos"].fillna(0) + df["Banos"].fillna(0)
    df = df.drop(columns=["Banos"], errors="ignore")

    # Corregimos valores
    df["Calefaccion"] = df["Calefaccion"].replace('Suelo Radiante', 'Suelo radiante')
    df["Calefaccion"] = df["Calefaccion"].replace(["Gas ciudad"], "Gas")

    # Corregir abreviaturas
    df["Puerta"] = df["Puerta"].replace(["IZQUIERDA", "izq", "izda", "IZ", "izq.", "Izq", "Izq.","IZQUQIERDA", "Izda","IZ","Izquierda","izquierda"], "IZQ")
    df["Puerta"] = df["Puerta"].replace(["DERECHA", "DR", "DRC", "derecha", "dcha", "d", "DCHA","dcha."], "DRE")

    df["Planta"] = df["Planta"].replace(["BJ", "bj", "bajo", "Baja", "BAJA", "BAJO" "baja", "Bjo y 1º","00"], "0")
    df["Planta"] = df["Planta"].replace(["EN"], "ENTRESUELO")
    df["Planta"] = df["Planta"].replace(["1"], "01")
    df["Planta"] = df["Planta"].replace(["2"], "02")
    df["Planta"] = df["Planta"].replace(["3"], "03",)
    df["Planta"] = df["Planta"].replace(["4"], "04")
    df["Planta"] = df["Planta"].replace(["5"], "05")
    df["Planta"] = df["Planta"].replace(["6"], "06")
    df["Planta"] = df["Planta"].replace(["7"], "07")
    df["Planta"] = df["Planta"].replace(["8"], "08")
    df["Planta"] = df["Planta"].replace(["9"], "09")

    # Sustituimos nombres en Zona
    df["Zona"] = df["Zona"].replace(["Monte Cerrau", "el Monte Cerrau"], "Monte Cerrao")
    df["Zona"] = df["Zona"].replace(["el Vallobin"], "Vallobin")
    df["Zona"] = df["Zona"].replace(["L'argañosa"], "La Argañosa")
    df.loc[df["Zona"].str.contains("Corredoria", na=False), "Zona"] = "Corredoria"
    df.loc[df["Zona"].str.contains("Olloniego", na=False), "Zona"] = "Olloniego"
    df.loc[df["Zona"].str.contains("Colloto", na=False), "Zona"] = "Colloto"
    df.loc[df["Zona"].str.contains("el Rancho", na=False), "Zona"] = "El Rancho"
    df["Zona"] = df["Zona"].replace(["Cimavilla"], "Cimadevilla")
    df["Zona"] = df["Zona"].replace(["el Cerilleru"], "El Cerillero")
    df["Zona"] = df["Zona"].replace(["Llano"], "El Llano")
    df["Zona"] = df["Zona"].replace(["L'arena"], "La Arena")
    df.loc[df["Zona"].str.contains("Ceares", na=False), "Zona"] = "Ceares"
    df.loc[df["Zona"].str.contains("Jove", na=False), "Zona"] = "Jove"

    # Corregimos nombres en Municipio
    df["Municipio"] = df["Municipio"].replace(["REGUERAS (LAS)"], "Las Regueras")
    df["Municipio"] = df["Municipio"].replace(["TAPIA DE CASARIEGO"], "Tapia de Casariego")
    df["Municipio"] = df["Municipio"].replace(["CANGAS DE ONIS"], "Cangas de Onis")
    df["Municipio"] = df["Municipio"].replace(["SAN MARTIN DEL REY AURELIO"], "San Martin del Rey Aurelio")

    # Sustituimos nombres de Poblaciones
    df.loc[df["Poblacion"].str.contains("Llangreu", na=False), "Poblacion"] = "Langreo"
    df["Poblacion"] = df["Poblacion"].replace(["Samartin del Rei Aurelio"], "San Martin del Rey Aurelio")
    df.loc[df["Poblacion"].str.contains("Grau", na=False), "Poblacion"] = "Grado"    

    # Poner en mayúscula el primer caracter
    df["Municipio"] = df["Municipio"].str.title()
    df["Poblacion"] = df["Poblacion"].str.title()
    df["Zona"] = df["Zona"].str.title()
    df["Direccion"] = df["Direccion"].str.title()

    # Convertir a columnas booleanas
    df["PlataformaCRM"] = df["PlataformaCRM"].isin(["gestioninmo"])
    df["Orientacion"] = df["Orientacion"].isin(["Sur", "Sur::Este", "Norte::Sur::Este::Oeste", "Sur::Oeste","Norte::Sur::Este", "Sur::Este::Oeste", "Norte::Sur"])
    df["Ascensor"] = df["Ascensor"].apply(lambda x: True if x >= 1 else (False if x == 0 else np.nan))
    df["Piscina"] = np.where(
        (df["Piscina"] >= 1) & ((df["PiscinaPropia"] == True) | (df["PiscinaComunitaria"] == True)), 
        True, 
        np.where(df["Piscina"] == 0, False, np.nan)
    )
    df["Garajes"] = df["Garajes"].apply(lambda x: True if x >= 1 else (False if x == 0 else np.nan))
    df["Trastero"] = df["Trastero"].apply(lambda x: True if x >= 1 else (False if x == 0 else np.nan))

    # Tratar los valores 0 como valores nulos en columnas numéricas
    df["CP"] = df["CP"].replace(0, None)
    df["Metros_Construidos"] = df["Metros_Construidos"].replace(0, None)
    df["Metros_Utiles"] = df["Metros_Utiles"].replace(0, None)
    df["Metros_Parcela"] = df["Metros_Parcela"].replace(0, None)
    df["Metros_Terraza"] = df["Metros_Terraza"].replace(0, None)
    df["Metros_Jardin"] = df["Metros_Jardin"].replace(0, None)
    df["Metros_Patio"] = df["Metros_Patio"].replace(0, None)
    df["PrecioRebajado"] = df["PrecioRebajado"].replace(0, None)
    df["Antiguedad"] = df["Antiguedad"].replace(0, None)

    # Eliminar etiquetas HTML
    html_tag_pattern = re.compile(r'<.*?>')
    df["Observaciones_Publicas"] = df["Observaciones_Publicas"].apply(lambda x: re.sub(html_tag_pattern, '', x) if isinstance(x, str) else x)

    return df


def rename_columns(df: pd.DataFrame) -> pd.DataFrame:
    try:
        # Renombramos columnas
        df = df.rename(columns={'Orientacion': 'CheckOrientacionSur'})
        df = df.rename(columns={'Ascensor': 'CheckAscensor'})
        df = df.rename(columns={'Piscina': 'CheckPiscina'})
        df = df.rename(columns={'Garajes': 'CheckGaraje'})
        df = df.rename(columns={'Trastero': 'CheckTrastero'})
        df = df.rename(columns={'Aseos': 'NumAseos'})
        df = df.rename(columns={'Dormitorios': 'NumDormitorios'})
        df = df.rename(columns={'Terraza': 'NumTerrazas'})
        df = df.rename(columns={'Zona': 'Barrio'})
        df = df.rename(columns={'PlataformaCRM': 'PrioridadRK'})
    except Exception as e:
        logger.error(f"Ha ocurrido un error al renombrar las columnas {e}")
    finally:
        return df
    

def remove_rows(df: pd.DataFrame) -> pd.DataFrame:
    try:
        # Eliminamos filas
        df = df[~df["Estado"].isin(["Reservado", "Baja"])]
    except Exception as e:
            logger.error(f"Ha ocurrido un error al eliminar ciertas filas {e}")
    finally:
        return df
    

#------ENRICHMENT FUNCTIONS------

def calculate_flat_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> int:
    """
    Calcula la distancia plana entre dos puntos en un plano cartesiano aproximado.
    :param lat1, lon1, lat2, lon2: Coordenadas de los puntos (en grados).
    :return: Distancia en metros.
    """
    # Convertir grados a metros (aproximación 1 grado ~ 111139 metros)
    distance = 10000
    try:
        delta_lat = (lat2 - lat1) * 111139
        delta_lon = (lon2 - lon1) * 111139 * math.cos(math.radians(lat1))
        distance = math.sqrt(delta_lat**2 + delta_lon**2)
    except Exception as e:
        logger.error(f"Ha ocurrido un error al calcular las distancias {e}")
    finally:
        return distance


def add_localizations(df: pd.DataFrame, locations: List[Dict]) -> pd.DataFrame:
    """
    Filtra y actualiza un DataFrame agregando información basada en un JSON de ubicaciones.
    :param dataframe: DataFrame con columnas 'Latitud' y 'Longitud'.
    :param json_file_path: Ruta al archivo JSON que contiene los datos de ubicación.
    :return: DataFrame actualizado.
    """
    try:
        for loc in locations:
            loc_lat = float(loc["lat"])
            loc_lon = float(loc["lon"])
            loc_description = loc["description"]
            loc_column = loc["column"]
            loc_radio = loc["radio"]
            loc_type = loc["type"]

            if loc_column not in df.columns:
                df[loc_column] = None # Crear la columna si no existe

            for index, row in df.iterrows():
                row_lat = row["Latitud"]
                row_lon = row["Longitud"]
                distance = calculate_flat_distance(row_lat, row_lon, loc_lat, loc_lon)
                if distance <= loc_radio:
                    if loc_type == "TEXT":
                        df.at[index, loc_column] = loc_description
                    elif loc_type == "BOOLEAN":
                        df.at[index, loc_column] = True
    except Exception as e:
        logger.error(f"Ha ocurrido un error al intentar agregar valores de localizaciones {e}")
    finally:
        return df


