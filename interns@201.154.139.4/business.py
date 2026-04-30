import asyncio
import ipaddress
import random
import sys

from concurrent.futures import ThreadPoolExecutor
from ipaddress import IPv4Network


sys.path.append("/home/ngsop/lilaApp/plugins/utilidadesPlugins")
from loggingConfig import LoggerFileConfig
from constantesPlugins import LOG_CONFIG_FILES
logging = LoggerFileConfig().crearLogFile(LOG_CONFIG_FILES.get("blacklist_check"))


from business import creacion_archivo
from constants import constantes
from utils import utils
from models import models

async def consulta_exhaustiva(direcciones, loop, executor):
    """
    Funcion que evalua todas las direcciones de un bloque

    Args:
        list: lista donde contiene las direcciones de un bloque a analizar
        loop: administrador de tareas que organiza el tráfico de red
        executor: grupo de hilos de apoyo
        

    Returns:
        dict: diccionario que contiene la ip y los dominios donde se encontro
    """
    print("Iniciando analisis completo")
    consulta_completa = [
        loop.run_in_executor(executor, utils.consultar_dominios, str(direccion)) for direccion in direcciones
    ]

    resultados = await asyncio.gather(*consulta_completa)
    
    
    return resultados

def obtener_muestra(sub_bloque):
    """
    Funcion donde obtenemos muestra en base al prefijo del sub_bloque

    Args:
        string: Cadena que contiene el sub bloque 

    Returns:
        list: lista donde se encuentran las direcciones muestra obtenidas 
    """
    todas = list(sub_bloque.hosts())
    direcciones_muestra = []

    # Determinamos el tamaño de la muestra según el prefijo
    if sub_bloque.prefixlen == 24:
        objetivo = constantes.MUESTRA_24
    elif sub_bloque.prefixlen == 16:
        objetivo = constantes.MUESTRA_16
    else:
        objetivo = 5

    if objetivo > 0:
        if len(todas) <= objetivo:
            direcciones_muestra = todas[:]
        else:
            primera = todas[0]
            ultima = todas[-1]

            centro = todas[1:-1]
            
            centro_aleatorio = random.sample(centro, objetivo - 2)
            direcciones_muestra = [primera] + centro_aleatorio + [ultima]
    else:
        direcciones_muestra = []

    return direcciones_muestra

async def evaluar_muestra(resultados_muestra, muestra, sub_bloque, loop, executor):
    
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
    
    porcentaje = conteo_positivos / len(muestra)
    
    if porcentaje >= constantes.UMBRAL:
        print(f"{sub_bloque} terminado con resultado de: BLOQUEO")
        
        return models.ResultadoBloque(
            bloque = str(sub_bloque),
            resultado = "BLOQUEO"
        )
        
    elif conteo_positivos == 0:
        print(f"{sub_bloque} terminado con resultado de: LIMPIO")

        return models.ResultadoBloque(
            bloque = str(sub_bloque),
            resultado = "LIMPIO"
        )
    
    else:   
        red = ipaddress.ip_network(sub_bloque, strict=False)
        todas = list(red.hosts())
        
        # Excluir IPs ya consultadas en la muestra
        muestra_set = {str(ip) for ip in muestra}  # necesitas pasar muestra como parámetro
        restantes = [ip for ip in todas if str(ip) not in muestra_set]

        print(f"{sub_bloque} terminado con resultado de: AUDITORIA")
        hallazgos = await consulta_exhaustiva(restantes, loop, executor)
        
        print(f"Resultados obtenidos de: {red}" )
        
        hallazgos_verdaderos = [h for h in hallazgos if h is not None]

        return models.ResultadoBloque(
            bloque=str(sub_bloque),
            resultado="AUDITORIA",
            hallazgos=hallazgos_verdaderos
        )

async def analizar_sub_bloques(sub_bloque, loop, executor):
    """
    Funcion que obtiene direcciones individuales de cada bloque y consulta muestreo

    Args:
        string: cadena que contiene el bloque que se analizará

    Returns:
        string: resultado del metodo analizar_bloque
    """

    sub_bloque_base = ipaddress.ip_network(sub_bloque, strict=False)
            
    muestra = obtener_muestra(sub_bloque_base) 

    muestreo = [
        loop.run_in_executor(executor, utils.consultar_dominios, str(ip)) for ip in muestra
    ]
    resultados_muestra = await asyncio.gather(*muestreo)

    resultado_analisis = await evaluar_muestra(resultados_muestra, muestra, sub_bloque, loop, executor)
    
    return resultado_analisis

async def procesar_sub_bloques(sub_bloques):
    """
    Funcion que orquesta el analisis de los sub-bloques

    Args:
        lista: Lista con los sub-bloques a analizar

    Returns:
        dict: Diccionario con resultados del analisis de los sub-bloques
    """
    
    loop = asyncio.get_running_loop() 
    executor = ThreadPoolExecutor(max_workers = constantes.MAX_WORKERS)
    try:
      
        logging.info(f"Iniciando analisis de sub-bloques")
        tareas = [analizar_sub_bloques(sub_bloque, loop, executor) for sub_bloque in sub_bloques]

        resultados = await  asyncio.wait_for( asyncio.gather(*tareas), timeout = 300)
        
        reporte = {}
                
        for datos in resultados:
            bloque = datos.bloque
            
            reporte[bloque] = {
                "ips": datos.hallazgos,
                "resultado": datos.resultado
            }
    
        print("sub_bloques terminados")
        return reporte
    
    finally:
        print("Finalizando hilos")
        try:
            await loop.run_in_executor(None, executor.shutdown, True)
            print("Hilos finalizados")
        except (ValueError, RuntimeError):
            print (Exception)

def dividir_bloque(bloque):
    """
    Funcion que divide el bloque original en sub-bloques

    Args:
        string: Cadena que contiene el bloque original a dividir

    Returns:
        list: lista que contiene los subloques obtenidos
    """
    bloque_base = ipaddress.ip_network(bloque, strict = False)
    
    
    if bloque_base.prefixlen > 24: #Bloque mayor /24
        return list[bloque_base]
    if bloque_base.prefixlen >= 16:
        return list(bloque_base.subnets(new_prefix = constantes.PREFIJO_24))
    elif bloque_base.prefixlen < 16 and bloque_base.prefixlen >= 11:
        return list(bloque_base.subnets(new_prefix=constantes.PREFIJO_16))
    else: #Bloque demasiado grande
        return []

async def iniciar_blacklist(bloques):

    """
    Funcion principal, obtiene bloques y obtiene sus sub-bloques

    Args:
        string: redes a analizar

    Returns:
        string: None
    """

    resultados = {}

    respuesta = False

    for bloque in bloques:
        sub_bloques = [str(sub_bloque) for sub_bloque in dividir_bloque(bloque)]
        logging.info(f"Divison de {bloque} exitoso")

        for sub_bloque in sub_bloques:
            print(f"{sub_bloque}")
            
        try:

            respuesta = await procesar_sub_bloques(sub_bloques)
            
        except Exception as e:
            print(f"error:Error consultar -  {e}")
            return None
        
        if respuesta is None:
            print("error: consultar no devolvio resultados")
            return None
        
        resultados[str(bloque)] = {
        "bloques": respuesta
        }
        
    
    creacion_archivo.generar_reporte(resultados)

    

    return resultados