import sys
from typing import Tuple, List, Optional

sys.path.append("/home/ngsop/lilaApp/plugins/utilidadesPlugins")
from loggingConfig import LoggerFileConfig
from constantesPlugins import LOG_CONFIG_FILES

from utils.mongo_utils import obtener_subredes_de_mongo, actualizar_estado_ejecutado

logger = LoggerFileConfig().crearLogFile(LOG_CONFIG_FILES.get("blacklist_check"))


def obtener_bloques_a_procesar(bloques_directos: Optional[List[str]] = None) -> Tuple[Optional[str], List[str], bool]:
    """
    Decide la fuente de los bloques a analizar (parámetro directo de la CLI o cola de MongoDB).

    Returns:
        tuple: (id_doc, bloques, es_programada)
    """
    if bloques_directos:
        logger.info(f"Argumentos recibidos : {bloques_directos}")
        return None, bloques_directos, False

    logger.info("Sin argumentos directos — Consultando tareas pendientes en MongoDB...")
    id_doc, bloques = obtener_subredes_de_mongo()
    es_programada = id_doc is not None

    return id_doc, bloques, es_programada


def notificar_resultado_programada(es_programada: bool, id_doc: Optional[str]):
    """
    Si la tarea provino de MongoDB, actualiza su estado a 'Ejecutado'.
    """
    if es_programada and id_doc:
        actualizar_estado_ejecutado(id_doc)
        logger.info(
            f"Estado actualizado para ID {id_doc} — Java enviará el correo en los próximos 60 segundos."
        )