import asyncio
import sys
import json

from business import business

if __name__ == "__main__":

    bloques = ["200.67.0.0/19"]
    print("iniciando consulta")
    respuesta = asyncio.run(business.iniciar_blacklist(bloques))
    if respuesta is None:
        print("No se pudo completar el análisis")


"""
    if len(sys.argv) < 2:
    #logging.info("No se recibieron direcciones ")
    print("No se recibieron direcciones ")
    else:
    bloques = sys.argv[1:]
    #logging.info("Argumentos recibidos:"+ str(lista_direcciones))

    respuesta_validacion_subredes = respuesta = asyncio.run(comprobar_subredes_blacklist(bloques))
    if respuesta_validacion_subredes:
        json_string = json.dumps(respuesta_validacion_subredes, indent=4)
        print(json_string)
    """
