import asyncio
import sys
import os
import json

sys.path.append("/home/ngsop/lilaApp/plugins/utilidadesPlugins")
from loggingConfig import LoggerFileConfig
from constantesPlugins import LOG_CONFIG_FILES
logging = LoggerFileConfig().crearLogFile(LOG_CONFIG_FILES.get("blacklist_check"))


from business import business

if __name__ == "__main__":
    if len(sys.argv) < 2:
        logging.info("No se recibieron direcciones")

    else:
        bloques = sys.argv[1:]
        logging.info("Argumentos recibidos:"+ str(bloques))

        respuesta_consulta_subredes = asyncio.run(business.iniciar_blacklist(bloques))
        if respuesta_consulta_subredes:
            logging.info("Proceso concluido")
            print (os.path.abspath(respuesta_consulta_subredes))



"""
    bloques = ["200.67.0.0/20", "192.168.1.0/21"]
        print("iniciando consulta")
        respuesta = asyncio.run(business.iniciar_blacklist(bloques))
        if respuesta is None:
            print("No se pudo completar el análisis")    
"""
