from typing import Dict

confirmation_fields = ["Poblacion", "Municipio", "Direccion", "NumDormitorios", "Precio"]

def extract_data(data_inm: Dict[str, str]) -> Dict[str, str]: 

    return {key: value for key, value in data_inm.items() if key in confirmation_fields}