import asyncio
import ipaddress
import sys

from concurrent.futures import ThreadPoolExecutor
from pymongo import MongoClient
from datetime import datetime

sys.path.append("/home/ngsop/lilaApp/plugins/utilidadesPlugins")
from loggingConfig import LoggerFileConfig
from constantesPlugins import LOG_CONFIG_FILES
logging = LoggerFileConfig().crearLogFile(LOG_CONFIG_FILES.get("blacklist_check"))

from constants import constantes
from utils import utils
from models import models


def guardar_en_mongo(resultados):
    """
    Guarda los resultados del análisis en MongoDB.

    Estructura del documento guardado:
    {
        "fecha": "2026-05-13 10:00:00",
        "bloques": {
            "200.67.0.0/16": {
                "bloques": {
                    "200.67.0.0/24": {
                        "resultado": "LIMPIO",
                        "ips": []
                    },
                    "200.67.1.0/24": {
                        "resultado": "BLOQUEO",
                        "ips": [{"ip": "200.67.1.5", "dominios": "zen.spamhaus.org"}]
                    },
                    "200.67.2.0/24": {
                        "resultado": "AUDITORIA",
                        "ips": [{"ip": "200.67.2.10", "dominios": "bl.spamcop.net"}]
                    }
                }
            }
        }
    }

    Args:
        dict: resultados generados por iniciar_blacklist

    Returns:
        None
    """
    cliente = None
    try:
        cliente = MongoClient("mongodb://admin:gsoppower@201.154.139.4:8445")
        db = cliente["blacklistDB"]
        coleccion = db["reportes"]

        documento = {
            "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "bloques": resultados
        }

        coleccion.insert_one(documento)

        logging.info("Resultados guardados en MongoDB correctamente")

    except Exception as e:
        logging.error(f"Error al guardar en MongoDB: {e}")

    finally:
        if cliente:
            cliente.close()



def obtener_muestra(sub_bloque):
    """
    Obtiene muestra de IPs según el prefijo del bloque.

    RN-05: /29 a /32 → todas las IPs utilizables
    RN-04: /24 a /28 → 4 IPs en posiciones fijas

    Args:
        sub_bloque: objeto IPv4Network

    Returns:
        list: lista de IPs a analizar
    """

    prefijo = sub_bloque.prefixlen

    # RN-05: /29 a /32 → todas las IPs
    if 29 <= prefijo <= 32:
        return list(sub_bloque.hosts())

    # RN-04: /24 a /28 → 4 IPs de muestra
    if 24 <= prefijo <= 28:

        hosts = list(sub_bloque.hosts())

        if len(hosts) <= 4:
            return hosts

       
        if prefijo == 24:
            offsets = [32, 96, 160, 224]
            muestra = []
            for offset in offsets:
                ip = sub_bloque.network_address + offset
                if ip in sub_bloque and ip != sub_bloque.broadcast_address:
                    muestra.append(ip)
            return muestra

        # Para /25 a /28: 4 posiciones proporcionales
        posiciones = [
            len(hosts) // 5,
            (len(hosts) * 2) // 5,
            (len(hosts) * 3) // 5,
            (len(hosts) * 4) // 5
        ]
        return [hosts[pos] for pos in posiciones]

    return []



async def analizar_por_fases(sub_bloque, loop, executor):
    """
    Análisis por fases para bloques /24 (provenientes de /16 a /23).

    Fase 1: 4 IPs  → LIMPIO si no hay hallazgos
    Fase 2: 10 IPs → AUDITORIA si no hay hallazgos en fase 2
    Fase 3: 11 IPs → BLOQUEO si hay hallazgos, AUDITORIA si no

    Args:
        sub_bloque: string con el bloque CIDR
        loop:       event loop de asyncio
        executor:   ThreadPoolExecutor

    Returns:
        ResultadoBloque
    """

    red   = ipaddress.ip_network(sub_bloque, strict=False)
    hosts = list(red.hosts())

    # FASE 1: 4 IPs 
    fase1 = obtener_muestra(red)

    tareas = [
        loop.run_in_executor(executor, utils.consultar_dominios, str(ip))
        for ip in fase1
    ]
    resultados1 = await asyncio.gather(*tareas)
    hallazgos1  = [r for r in resultados1 if r is not None]

    if not hallazgos1:
        return models.ResultadoBloque(
            bloque=str(sub_bloque),
            resultado="LIMPIO"
        )

    # FASE 2: 10 IPs más
    fase1_set  = set(fase1)
    restantes  = [ip for ip in hosts if ip not in fase1_set]
    fase2      = restantes[:10]

    tareas = [
        loop.run_in_executor(executor, utils.consultar_dominios, str(ip))
        for ip in fase2
    ]
    resultados2 = await asyncio.gather(*tareas)
    hallazgos2  = [r for r in resultados2 if r is not None]

    if not hallazgos2:
        return models.ResultadoBloque(
            bloque=str(sub_bloque),
            resultado="AUDITORIA",
            hallazgos=hallazgos1
        )

    #FASE 3: 11 IPs más 
    fase2_set  = set(fase2)
    restantes  = [ip for ip in restantes if ip not in fase2_set]
    fase3      = restantes[:11]

    tareas = [
        loop.run_in_executor(executor, utils.consultar_dominios, str(ip))
        for ip in fase3
    ]
    resultados3 = await asyncio.gather(*tareas)
    hallazgos3  = [r for r in resultados3 if r is not None]

    todos_hallazgos = hallazgos1 + hallazgos2 + hallazgos3

    if hallazgos3:
        return models.ResultadoBloque(
            bloque=str(sub_bloque),
            resultado="BLOQUEO",
            hallazgos=todos_hallazgos
        )

    return models.ResultadoBloque(
        bloque=str(sub_bloque),
        resultado="AUDITORIA",
        hallazgos=todos_hallazgos
    )




async def evaluar_muestra(resultados_muestra, muestra, sub_bloque, loop, executor):
    """
    Evalúa resultado de muestra para bloques /24 a /32.

    Sin hallazgos → LIMPIO
    Con hallazgos → AUDITORIA

    Args:
        resultados_muestra: resultados de la consulta
        muestra:            IPs consultadas
        sub_bloque:         bloque analizado
        loop:               event loop
        executor:           ThreadPoolExecutor

    Returns:
        ResultadoBloque
    """

    hallazgos = [r for r in resultados_muestra if r is not None]

    if len(hallazgos) == 0:
        return models.ResultadoBloque(
            bloque=str(sub_bloque),
            resultado="LIMPIO"
        )

    return models.ResultadoBloque(
        bloque=str(sub_bloque),
        resultado="AUDITORIA",
        hallazgos=hallazgos
    )




async def analizar_sub_bloques(sub_bloque, loop, executor, analisis_fases):
    """
    Analiza un sub-bloque según su tipo.

    analisis_fases=True  → RN-06 (bloques /24 provenientes de /16-/23)
    analisis_fases=False → RN-04/RN-05 (bloques /24 a /32 directos)

    Args:
        sub_bloque:     string con el bloque CIDR
        loop:           event loop
        executor:       ThreadPoolExecutor
        analisis_fases: bool

    Returns:
        ResultadoBloque
    """

    sub_bloque_base = ipaddress.ip_network(sub_bloque, strict=False)

    # RN-06: análisis por fases
    if analisis_fases:
        return await analizar_por_fases(sub_bloque, loop, executor)

    # RN-04 y RN-05: muestreo simple
    muestra = obtener_muestra(sub_bloque_base)

    muestreo = [
        loop.run_in_executor(executor, utils.consultar_dominios, str(ip))
        for ip in muestra
    ]
    resultados_muestra = await asyncio.gather(*muestreo)

    return await evaluar_muestra(
        resultados_muestra,
        muestra,
        sub_bloque,
        loop,
        executor
    )



async def procesar_sub_bloques(sub_bloques):
    """
    Orquesta el análisis paralelo de todos los sub-bloques.

    Args:
        sub_bloques: lista de tuplas (sub_bloque, analisis_fases)

    Returns:
        dict: { sub_bloque: { "ips": [...], "resultado": "..." } }
    """

    loop     = asyncio.get_running_loop()
    executor = ThreadPoolExecutor(max_workers=constantes.MAX_WORKERS)

    try:
        logging.info("Iniciando análisis de sub-bloques")

        tareas = [
            analizar_sub_bloques(sub_bloque, loop, executor, analisis_fases)
            for sub_bloque, analisis_fases in sub_bloques
        ]

        resultados = await asyncio.wait_for(
            asyncio.gather(*tareas),
            timeout=300
        )

        reporte = {}
        for datos in resultados:
            reporte[datos.bloque] = {
                "ips":       datos.hallazgos,
                "resultado": datos.resultado
            }

        logging.info("Análisis de sub-bloques terminado")
        return reporte

    finally:
        try:
            await loop.run_in_executor(None, executor.shutdown, True)
        except (ValueError, RuntimeError) as e:
            logging.error(f"Error cerrando executor: {e}")



def dividir_bloque(bloque):
    """
    Divide el bloque en sub-bloques y determina el tipo de análisis.

    Returns:
        list de tuplas: [(sub_bloque_str, analisis_fases), ...]

    Raises:
        ValueError: si el prefijo es menor a /16 (RN-07)
    """

    bloque_base = ipaddress.ip_network(bloque, strict=False)
    prefijo     = bloque_base.prefixlen

    # RN-07: rechazar /12 a /15 y menores
    if prefijo < 16:
        raise ValueError(f"Segmento no soportado: /{prefijo}. Solo se aceptan /16 a /32")

    # RN-06: /16 a /23 → subdividir en /24, análisis por fases
    if 16 <= prefijo <= 23:
        return [
            (str(sub), True)
            for sub in bloque_base.subnets(new_prefix=24)
        ]

    # RN-04: /24 a /28 → análisis simple con 4 IPs
    # RN-05: /29 a /32 → todas las IPs
    return [(str(bloque_base), False)]


async def iniciar_blacklist(bloques):
    """
    Función principal. Recibe los bloques, los divide y lanza el análisis.

    Args:
        bloques: lista de strings con bloques en formato CIDR

    Returns:
        dict: resultados del análisis por bloque
    """

    resultados = {}

    for bloque in bloques:

        try:
            sub_bloques = dividir_bloque(bloque)

            logging.info(f"División de {bloque} exitosa — {len(sub_bloques)} sub-bloques")

            respuesta = await procesar_sub_bloques(sub_bloques)

            if respuesta is None:
                logging.error(f"No hubo respuesta para {bloque}")
                continue

            resultados[str(bloque)] = {
                "bloques": respuesta
            }

        except ValueError as e:
            logging.error(f"Bloque rechazado {bloque}: {e}")
            resultados[str(bloque)] = {"error": str(e)}

        except Exception as e:
            logging.error(f"Error procesando {bloque}: {e}")
            resultados[str(bloque)] = {"error": str(e)}

    guardar_en_mongo(resultados)

    return resultados