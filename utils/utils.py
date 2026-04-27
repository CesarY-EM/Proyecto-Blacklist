import threading

from pydnsbl import DNSBLIpChecker
from pydnsbl.providers import BASE_PROVIDERS

from constants import constantes

_local= threading.local()

def obtener_checker():
    
    if not hasattr(_local, "checker"):
        dominios = constantes.PROVIDERS        
        _local.checker = DNSBLIpChecker(providers=dominios, timeout=2)
    return _local.checker

def consultar_dominios(direccion):
    """
    Funcion que verifica si direccion ingresada se encuentra en listas nehras

    Args:
        string: ip a verificar
        string: providers a agregar para contemplarlos para consulta

    Returns:
        dict: Contiene la direccion y dominios donde se encontro 
                (Si la direccion no se encontro en ningun dominio no se pasara nada)
    """

    try:
        checker = obtener_checker()
        resultado = checker.check(direccion)

        if resultado.blacklisted:
            dominios = (
                ", ".join(resultado.detected_by.keys()) if resultado.detected_by else ""
            )
            return {"ip": direccion, "dominios": dominios}
    except Exception as e:
        return None