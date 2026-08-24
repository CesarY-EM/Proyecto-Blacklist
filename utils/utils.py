import sys
import threading
from datetime import datetime, timezone
from pydnsbl import DNSBLIpChecker

sys.path.append("/home/ngsop/lilaApp/core")
from db.connectionDB import mongoConnection
from utilidades.constantes import MONGO_DEFAULT_LILA

sys.path.append("/home/ngsop/lilaApp/plugins/utilidadesPlugins")
from loggingConfig import LoggerFileConfig
from constantesPlugins import LOG_CONFIG_FILES

from constants.constants import Constants

logging = LoggerFileConfig().crearLogFile(LOG_CONFIG_FILES.get("blacklist_check"))
_threading_local = threading.local()
COLECCION_PROGRAMACIONES = "programaciones"


# MÉTODOS DE BASE DE DATOS 

def _obtener_coleccion_programaciones():
    """Obtiene la colección 'programaciones' desde el pool de Mongo de LILA."""
    db = mongoConnection.get_db(MONGO_DEFAULT_LILA)
    return db[COLECCION_PROGRAMACIONES]


def obtener_subredes_de_mongo():
    """
    Obtiene la programación Pendiente más antigua usando la conexión de LILA.
    Returns:
        tuple: (_id, lista_subredes)
    """
    try:
        coleccion = _obtener_coleccion_programaciones()
        resultado = coleccion.find_one(
            {"estado": "Pendiente"},
            sort=[("fechaCreacion", 1)]
        )

        if resultado:
            logging.info(f"Programación encontrada: {resultado}")
            return resultado["_id"], resultado.get("subredes", [])

        logging.warning("No se encontró ninguna programación pendiente")
        return None, []

    except Exception as e:
        logging.error(f"Error obteniendo la programación pendiente de MongoDB: {e}")
        return None, []


def actualizar_estado_ejecutado(id_doc):
    """
    Actualiza el estado de la tarea en MongoDB a 'Ejecutado'.
    """
    try:
        coleccion = _obtener_coleccion_programaciones()
        coleccion.update_one(
            {"_id": id_doc},
            {
                "$set": {
                    "estado": "Ejecutado",
                    "fechaModificacion": datetime.now(timezone.utc)
                }
            }
        )
        logging.info(f"Estado de la programación {id_doc} actualizado a 'Ejecutado'.")
    except Exception as e:
        logging.error(f"Error al actualizar estado en Mongo para ID {id_doc}: {e}")


# MÉTODOS DE CONSULTA DNSBL

def obtener_checker():
    """Obtiene una instancia local de DNSBLIpChecker por hilo de ejecución."""
    if not hasattr(_threading_local, "checker"):
        proveedores = Constants.PROVIDERS
        _threading_local.checker = DNSBLIpChecker(providers=proveedores, timeout=2)
    return _threading_local.checker


def consultar_ip_en_blacklist(direccion):
    """
    Verifica si una dirección IP ingresada se encuentra en listas negras.

    Args:
        direccion (str): IP a verificar.

    Returns:
        dict | None: Contiene la dirección y dominios detectados (o None si limpia/error).
    """
    try:
        checker = obtener_checker()
        resultado = checker.check(direccion)

        if resultado.blacklisted:
            dominios = (
                ", ".join(resultado.detected_by.keys()) if resultado.detected_by else ""
            )
            return {"ip": direccion, "dominios": dominios}
    except Exception:
        return None
    return None