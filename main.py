import sys
import json
from jsonschema import validate, ValidationError


sys.path.append("/home/ngsop/lilaApp/plugins/utilidadesPlugins")
from business.business_analisis import principal


ESQUEMA_ENTRADA = {
    "type": "array",
    "minItems": 1,
    "items": {
        "type": "string",
        "minLength": 1
    }
}

def validar_y_obtener_bloques(json_raw: str) -> list:
    """
    Parsea y valida que el texto JSON recibido cumpla con la estructura esperada.
    Lanza excepciones claras si la entrada no es válida.
    """
    # Paso A: Convertir texto a objeto de Python
    datos = json.loads(json_raw)
    
    # Paso B: Validar tipo y contenido con el esquema
    validate(instance=datos, schema=ESQUEMA_ENTRADA)
    
    return datos

if __name__ == "__main__":
    if len(sys.argv) > 1:
        try:
            lista_bloques = validar_y_obtener_bloques(sys.argv[1])
            
            principal(bloques_directos=lista_bloques)

        except json.JSONDecodeError:
            print(json.dumps({"status": "ERROR", "message": "El argumento no es un JSON válido."}))
            sys.exit(1)
            
        except ValidationError as e:
            print(json.dumps({"status": "ERROR", "message": f"Formato incorrecto: {e.message}"}))
            sys.exit(1)
            
    else:
        principal()