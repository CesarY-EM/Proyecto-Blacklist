import pydnsbl
import asyncio
import ipaddress
import csv
import ipaddress
import csv
import random
import threading

from pydnsbl import DNSBLIpChecker
from concurrent.futures import ThreadPoolExecutor
from ipaddress import IPv4Network
from datetime import datetime


_local= threading.local()


MAX_WORKERS = 25
UMBRAL = 0.8
MUESTRA = 15


def obtener_checker():

    if not hasattr(_local, "checker"):
        _local.checker = DNSBLIpChecker(timeout=2)
    return _local.checker


def validar(bloques):

    """
    Funcion para validar si los bloques ingresados tienen el formato CIDR correcto

    Args:
        string: Bloques a validar

    Returns:
        list: Lista con los bloques que si tiene el formato correcto (se descartan los invalidos)
    """

    validos = []
    invalidos = []

    for bloque in bloques:
        try:
            red = IPv4Network(bloque.strip(), strict=False)
            validos.append(red)
        except ValueError as e:
            invalidos.append({"bloque": bloque.strip(), "error": str(e)})

    return validos


def verificar_ip(ip, providers=None):

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
        resultado = checker.check(ip)

        if resultado.blacklisted:
            dominios = (
                ", ".join(resultado.detected_by.keys()) if resultado.detected_by else ""
            )
            return {"ip": ip, "dominios": dominios}
        return None
    except Exception:
        return None

def evaluar(resultados_muestra, total_muestra):
    
    """
    Funcion que evalua el resultado de las direcciones muestra

    Args:
        list: lista de las direcciones con hallazgos
        int: Numero del total de las direcciones muestra que se analizaron
        

    Returns:
        string: cadena que indica el resultado del porcentaje resultante
    """
    
    positivos = [r for r in resultados_muestra if r is not None]
    conteo_positivos = len(positivos)
    

    porcentaje = conteo_positivos / total_muestra
    
    if porcentaje >= UMBRAL:
        return "BLOQUEO"
        
    if conteo_positivos == 0:
        return "LIMPIO"
        
    return "AUDITORIA"

async def consulta_exhaustiva(direcciones, loop, executor):

    consultar = [
        loop.run_in_executor(executor, verificar_ip, str(ip)) for ip in direcciones
    ]

    resultados = await asyncio.gather(*consultar)
    return resultados
    

async def analizar_bloques(bloque, loop, executor):

    """
    Funcion que obtiene direcciones individuales de cada bloque y consulta muestreo

    Args:
        string: cadena que contiene el bloque de donde se obtendran las direcciones individuales

    Returns:
        string: resultado del metodo analizar_bloque
    """

    red = ipaddress.ip_network(bloque, strict=False)
    todas = list(red.hosts())

    if len(todas) <= MUESTRA:
        muestra = todas[:]
    else:
        primera = todas[0]
        ultima = todas[-1]
        # Excluir primera y última para el muestreo
        centro = [ip for ip in todas if ip not in (primera, ultima)]
        centro_aleatorio = random.sample(centro, 13)
        muestra = [primera] + centro_aleatorio + [ultima]

    verificar_muestra = [
        loop.run_in_executor(executor, verificar_ip, str(ip)) for ip in muestra
    ]
    resultados_muestra = await asyncio.gather(*verificar_muestra)
    resultado = evaluar(resultados_muestra, len(muestra))
    
    if resultado == "BLOQUEO":
        print(f"{bloque} terminado")
        return {
            "bloque": str(bloque),
            "hallazgos":[],
            "muestras":[],
            "resultado": "BLOQUEO",
        }

    elif resultado == "LIMPIO":
        print(f"{bloque} terminado")
        return {
            "bloque": str(bloque),
            "hallazgos":[],
            "muestras":[],
            "resultado": "LIMPIO",
        }

    else:
        # AUDITORIA

        print(f"{bloque} terminado")
        hallazgos = await consulta_exhaustiva(todas, loop, executor)
        
        return {
            "bloque": str(bloque),
            "hallazgos": hallazgos,
            "muestras": [],
            "resultado": "AUDITORIA",
        }


async def consultar(bloques):
    
    loop = asyncio.get_running_loop() 
    executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)
    
    try:
        print(">>> Iniciando análisis asíncrono...")

        tareas = [analizar_bloques(b, loop, executor) for b in bloques]
        resultados = await asyncio.gather(*tareas)
        
        reporte = {}
        for r in resultados:
            bloque = r["bloque"]
            reporte[bloque] = {"ips" : r["hallazgos"],
                                "resultado": r["resultado"]
                                }
    
        return reporte
    
    finally:
        try:
            await loop.run_in_executor(None, executor.shutdown, True)
        except ValueError:
            pass
        