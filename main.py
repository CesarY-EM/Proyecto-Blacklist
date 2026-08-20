import asyncio
import sys
import json
from datetime import datetime, timezone

sys.path.append("/home/ngsop/lilaApp/plugins/utilidadesPlugins")
from loggingConfig import LoggerFileConfig
from constantesPlugins import LOG_CONFIG_FILES
logging = LoggerFileConfig().crearLogFile(LOG_CONFIG_FILES.get("blacklist_check"))

sys.path.append("/home/ngsop/lilaApp/core")
from db.connectionDB import mongoConnection
from utilidades.constantes import MONGO_DEFAULT_LILA

from business import business

COLECCION_PROGRAMACIONES = "programaciones"


def obtener_subredes_de_mongo():
    """
    Obtiene la programación Pendiente más antigua.
    Retorna (_id, lista_subredes)
    """
    try:
        cliente = MongoClient(
            "mongodb://admin:gsoppower@201.154.139.4:8445"
        )

        db = cliente["blacklistDB"]
        coleccion = db["programaciones"]

        resultado = coleccion.find_one(
            {"estado": "Pendiente"},
            sort=[("fechaCreacion", 1)]
        )

        cliente.close()

        if resultado:
            logging.info(f"Programación encontrada: {resultado}")

            return (
                resultado["_id"],
                resultado.get("subredes", [])
            )

        logging.warning("No se encontró ninguna programación pendiente")
        return None, []

    except Exception as e:
        logging.error(f"Error leyendo MongoDB: {e}")
        return None, []


def obtener_bloques_a_procesar(bloques_directos):
    """
    Responsabilidad única: decidir de dónde vienen los bloques a analizar
    (parámetro directo o cola de MongoDB) y devolver un resultado uniforme.

    Returns:
        tuple: (id_doc, bloques, es_programada)
    """
    if bloques_directos:
        logging.info(f"Argumentos recibidos por parámetro: {bloques_directos}")
        return None, bloques_directos, False

    logging.info("Sin argumentos directos — Consultando base de datos por tareas programadas...")
    id_doc, bloques = obtener_subredes_de_mongo()
    return id_doc, bloques, True


def notificar_resultado_programada(es_programada, id_doc):
    """
    Responsabilidad única: si la tarea viene de la cola de Mongo,
    actualizar su estado para que Java dispare el correo.
    """
    if es_programada and id_doc:
        actualizar_estado_ejecutado(id_doc)
        logging.info(
            f"Estado actualizado para ID {id_doc} — Java enviará el correo en los próximos 60 segundos."
        )


def ejecutar(bloques_directos=None):
    """
    Método de entrada unificado y seguro.
    Es llamado por LILA Scheduler o por la ejecución directa de la terminal.
    """
    logging.info("=== Iniciando ejecución del Plugin Blacklist ===")

    id_doc, bloques, es_programada = obtener_bloques_a_procesar(bloques_directos)

    if not bloques:
        logging.error("No hay bloques que analizar — Abortando ejecucion.")
        return {"status": "NO_WORK"}

    logging.info(f"Iniciando análisis de {len(bloques)} bloque(s): {bloques}")

    # Ejecución de la lógica de negocio asíncrona
    respuesta = asyncio.run(business.iniciar_blacklist(bloques))

    if not respuesta:
        logging.error("El análisis no retornó resultados válidos.")
        return {"status": "FAILED"}

    logging.info("Análisis completado correctamente.")
    notificar_resultado_programada(es_programada, id_doc)

    print(respuesta)
    return {"status": "SUCCESS", "data": respuesta}


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Decodificamos el JSON que viene en sys.argv[1]
        lista_bloques = json.loads(sys.argv[1])
        ejecutar(bloques_directos=lista_bloques)
    else:
        ejecutar()