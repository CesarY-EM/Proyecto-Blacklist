import sys
import threading
import logging
from pydnsbl import DNSBLIpChecker
from constants.constantes import Constants

sys.path.append("/home/ngsop/lilaApp/plugins/utilidadesPlugins")
from loggingConfig import LoggerFileConfig
from constantesPlugins import LOG_CONFIG_FILES

logger = LoggerFileConfig().crearLogFile(LOG_CONFIG_FILES.get("blacklist_check"))

_threading_local = threading.local()


def obtener_checker():
    """Reutiliza o crea una instancia de DNSBLIpChecker por hilo (Thread-safe)."""
    if not hasattr(_threading_local, "checker"):
        _threading_local.checker = DNSBLIpChecker(providers=Constants.PROVIDERS)
    return _threading_local.checker


def consultar_ip_en_blacklist(direccion: str):
    """Realiza la consulta DNSBL para una dirección IP individual."""
    try:
        checker = obtener_checker()
        res = checker.check(direccion)

        if res.blacklisted:
            dominios = ", ".join([str(p) for p in res.detected_by])
            return {
                "ip": direccion,
                "dominios": dominios
            }
        return None

    except Exception as e:
        logging.error(f"Error consultando IP {direccion} en listas negras: {e}")
        return None