import sys
import logging
from datetime import datetime, timezone
from bson import ObjectId


sys.path.append("/home/ngsop/lilaApp/core")
from db.connectionDB import mongoConnection
from utilidades.constantes import MONGO_DEFAULT_LILA

sys.path.append("/home/ngsop/lilaApp/plugins/utilidadesPlugins")
from loggingConfig import LoggerFileConfig
from constantesPlugins import LOG_CONFIG_FILES

logger = LoggerFileConfig().crearLogFile(LOG_CONFIG_FILES.get("blacklist_check"))

COLECCION_PROGRAMACIONES = "programaciones"


def obtener_subredes_de_mongo():
    """Obtiene la tarea pendiente más antigua de la colección programaciones."""
    try:
        db = mongoConnection.get_db(MONGO_DEFAULT_LILA)
        coleccion = db[COLECCION_PROGRAMACIONES]

        documento = coleccion.find_one(
            {"estado": "Pendiente"},
            sort=[("fechaCreacion", 1)]
        )

        if not documento:
            logging.info("No hay tareas pendientes en MongoDB.")
            return None, []

        id_doc = str(documento["_id"])
        subredes = documento.get("parametros", {}).get("subredes", [])
        
        logging.info(f"Tarea encontrada [ID: {id_doc}] con subredes: {subredes}")
        return id_doc, subredes

    except Exception as e:
        logging.error(f"Error al consultar MongoDB: {e}", exc_info=True)
        return None, []


def actualizar_estado_ejecutado(id_doc: str):
    """Actualiza el estado del documento a 'Ejecutado' e inserta fechaModificacion UTC."""
    try:
        db = mongoConnection.get_db(MONGO_DEFAULT_LILA)
        coleccion = db[COLECCION_PROGRAMACIONES]

        resultado = coleccion.update_one(
            {"_id": ObjectId(id_doc)},
            {
                "$set": {
                    "estado": "Ejecutado",
                    "fechaModificacion": datetime.now(timezone.utc)
                }
            }
        )
        if resultado.modified_count > 0:
            logging.info(f"Tarea {id_doc} actualizada exitosamente a 'Ejecutado'.")
        else:
            logging.warning(f"No se pudo actualizar el estado de la tarea {id_doc}.")

    except Exception as e:
        logging.error(f"Error al actualizar estado en MongoDB: {e}", exc_info=True)