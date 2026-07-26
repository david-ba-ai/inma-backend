import os
from typing import Dict
import json
import openai
import requests
import sys
from typing import Dict
import urllib3
from datetime import datetime, timezone
from dotenv import load_dotenv

#------ CONSULTA GENERAL A LA API-----
def generate_api_request(url: str, data: Dict[str,str])-> Dict:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    try:
        response = requests.post(url, data=data, verify=False)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error occurred during the HTTP request: {e}")
        sys.exit(1)

    try:
        json_response = response.json()
    except ValueError:
        print("Error: La respuesta no es un objeto JSON válido.")
        json_response = {}
        
    return json_response

#------VARIABLES-----
load_dotenv()
page_url = os.getenv("CRM_API_URL_INMUEBLE") # URL de la API para obtener información de un inmueble
all_pages_url = os.getenv("CRM_API_URL_INMUEBLES") # URL de la API para obtener la totalidad de inmuebles
demand_url = os.getenv("CRM_API_URL_DEMANDA") # URL para grabar una demanda en la API


#------CUERPOS DE SOLICITUD------
# Cuerpo de solicitud a la API para obtener información de un inmueble
page_body = {
    'usuario': os.getenv("CRM_API_USERNAME"),
    'password': os.getenv("CRM_API_PASSWORD"),
    'Id' : 0,
}

# Cuerpo de solicitud a la API para obtener información de la totalidad de inmuebles
all_pages_body = {
    'usuario': os.getenv("CRM_API_USERNAME"),
    'password': os.getenv("CRM_API_PASSWORD"),
    'orden' : 'Id',
    'ascdesc': 'ASC',
    'numXpagina': 30,
    'pagina': 0
}

# Cuerpo de solicitud a la API para grabar una demanda
demand_body = {
    'usuario': os.getenv("CRM_API_USERNAME"),
    'password': os.getenv("CRM_API_PASSWORD"),
    'telefono' : None,
    'email': None,
    'id_inmueble': None,
    'observaciones' : None,
}

#------EJECUCIÓN DE LLAMADAS------

#------RECUPERAR INFO DE UN INMUEBLE
def fetch_page(id: int, url: str = page_url, body: Dict[str,str] = page_body) -> Dict[str, str]:
    """
    Realiza una llamada a la API y devuelve el resultado. Pensado para obtener información de un solo inmueble
    :parama url (str): URL donde se localiza el recurso
    :parama body (Dict[str,str]): cuerpo de solicitud a la API para obtener información de un inmueble
    :param id (str): identificador del inmueble a localizar.
    :returns: devuelve un diccionario con los campos de un inmueble.
    """

    body = body.copy()
    body["Id"] = id

    api_response = None
    try:
        api_response = generate_api_request(url, body)

    except Exception as e:
            print(f"Error al realizar la solicitud a la API: {e}")

    dict_inm = api_response.get("inmueble")
    
    return {key: value for key, value in dict_inm.items()}


#------RECUPERAR INFO DE VARIOS INMUEBLES
def fetch_all_pages(url: str = all_pages_url, body: Dict[str,str] = all_pages_body) -> Dict[str,Dict[str,str]]:
    """
    Hace llamadas iterativas a una API y devuelve una lista con los resultados. Pensado para obtener información de todos los inmuebles.
    :param url (str): URL del API con varias páginas
    :param body (str): cuerpo inicial para las solicitudes a la API.
    :return (Dict[str,Dict[str,str]]): diccionario con con todos los resultados como diccionarios combinados
    """

    all_results = {}
    current_page = 0
    
    while True:
        body = body.copy()
        body['pagina'] = current_page

        try:
            api_response = generate_api_request(url, body)

        except Exception as e:
            print(f"Error al realizar la solicitud a la API: {e}")
            break
        
        list_inm = api_response.get("inmuebles")
        if list_inm is None:
            break
        
        # Por cada diccionario de la lista creamos un nuevo par clave-valor en "all_results", con clave el campo 
        # "Id" del diccionario y valor un diccionario con el resto de campos que esten en requiered_fields 
        for item in list_inm:
            all_results[item["Id"]] = {key: value for key, value in item.items()}
        
        current_page += 1
    
    return all_results


#------GRABAR DEMANDA DE UN INMUEBLE
def fetch_demand(data: Dict[str,str], url: str = demand_url, body: Dict[str,str] = demand_body) -> Dict[str,Dict[str,str]]:
    """
    Realiza una llamada a la API y devuelve el resultado. Pensado para grabar una demanda de un inmueble.
    :parama url (str): URL donde se localiza el recurso
    :parama body (Dict[str,str]): cuerpo de solicitud a la API
    :returns: devuelve la respuesta de la API.
    """

    body = body.copy()

    body["nombre"] = data.get("nombre", None)
    body["telefono"] = data.get("telefono", None)
    body["email"] = data.get("email", None)
    body["id_inmueble"] = data.get("id_inmueble", None)
    
    observaciones = {
         "fuente": "mark_chatbot",
         "fuente": data.get("source"),
         "marca_de_tiempo": datetime.now(timezone.utc).isoformat()
    }
    body["observaciones"] = json.dumps(observaciones)
 
    api_response = None
    try:
        print(f"SIMULACIÓN DE DEMANDA: {body}")
        #api_response = generate_api_request(url, body) 
    except Exception as e:
        print(f"Error al realizar la solicitud a la API: {e}")
    
    return api_response


# ------TRANSCRIPCIÓN DE TEXTO CON WHISPER
async def transcribe_audio(file_path: str) -> str:
    """
    Envía un archivo de audio a la API de OpenAI y devuelve la transcripción como texto.
    """
    client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    try:
        with open(file_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="text",
                language="es"  # opcional
            )
        return transcript.strip()
    except Exception as e:
        raise

