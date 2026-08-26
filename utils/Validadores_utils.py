import ipaddress
from jsonschema import validate, ValidationError, draft7_format_checker

ENTRADA_BLACKLIST_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "array",
    "minItems": 1,
    "items": {
        "type": "string",
        "minLength": 1
    }
}

def is_valid(payload):
    """
    Valida que el payload de entrada sea una lista no vacía de cadenas de texto
    y que cada elemento corresponda a una IP o subred CIDR válida.
    """
    try:
        # Valida la estructura general con JsonSchema
        validate(instance=payload, schema=ENTRADA_BLACKLIST_SCHEMA, format_checker=draft7_format_checker)
        
        # Valida que cada cadena sea una IP o subred 
        for elemento in payload:
            ipaddress.ip_network(elemento, strict=False)
            
        return True
    except (ValidationError, ValueError, Exception):
        return False