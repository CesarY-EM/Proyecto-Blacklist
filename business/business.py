import asyncio
import ipaddress
import sys

from concurrent.futures import ThreadPoolExecutor
<<<<<<< HEAD
from pymongo import MongoClient
=======
>>>>>>> 26edf28 (Mejoras de legibilidad)
from datetime import datetime

sys.path.append("/home/ngsop/lilaApp/plugins/utilidadesPlugins")
from loggingConfig import LoggerFileConfig
from constantesPlugins import LOG_CONFIG_FILES
logging = LoggerFileConfig().crearLogFile(LOG_CONFIG_FILES.get("blacklist_check"))

<<<<<<< HEAD
=======
sys.path.append("/home/ngsop/lilaApp/core")
from db.connectionDB import mongoConnection
from utilidades.constantes import MONGO_DEFAULT_LILA

>>>>>>> 26edf28 (Mejoras de legibilidad)
from constants import constantes
from utils import utils
from models import models

COLECCION_REPORTES = "reportes"

def guardar_en_mongo(resultados):
    mongo_connection = None
    try:
        documento = {
            "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "bloques": resultados,
        }
        mongo_connection = mongoConnection(MONGO_DEFAULT_LILA)
        mongo_connection.saveData(documento, COLECCION_REPORTES)
        logging.info("Resultados guardados en MongoDB correctamente")

    except Exception as e:
        logging.error(f"Error al guardar en MongoDB: {e}")

    finally:
        if mongo_connection:
            try:
                mongo_connection.close()
            except Exception:
                pass


<<<<<<< HEAD

=======
>>>>>>> 26edf28 (Mejoras de legibilidad)
def obtener_muestra(sub_bloque):
    prefijo = sub_bloque.prefixlen

    if 29 <= prefijo <= 32:
        return list(sub_bloque.hosts())

    if 24 <= prefijo <= 28:
        hosts = list(sub_bloque.hosts())

        if len(hosts) <= 4:
            return hosts

        if prefijo == 24:
            offsets = [
                12,
                38,
                64,
                90,
                116,
                142,
                168,
                194,
                220,
                246
            ]
            muestra = []
            for offset in offsets:
                ip = sub_bloque.network_address + offset
                if ip in sub_bloque and ip != sub_bloque.broadcast_address:
                    muestra.append(ip)
            return muestra

        posiciones = [
            len(hosts) // 5,
            (len(hosts) * 2) // 5,
            (len(hosts) * 3) // 5,
            (len(hosts) * 4) // 5
        ]
        return [hosts[pos] for pos in posiciones]

    return []


async def consultar_fase(ips, loop, executor):
    """
<<<<<<< HEAD
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
=======
    Responsabilidad única: consultar una lista de IPs contra el blacklist
    y devolver solo los hallazgos (sin None).
    """
    tareas = [
        loop.run_in_executor(executor, utils.consultar_dominios, str(ip))
        for ip in ips
    ]
    resultados = await asyncio.gather(*tareas)
    return [r for r in resultados if r is not None]


async def analizar_por_fases(sub_bloque, loop, executor):
    red = ipaddress.ip_network(sub_bloque, strict=False)
    hosts = list(red.hosts())

    # Fase 1: 4 IPs
    fase1 = obtener_muestra(red)
    hallazgos1 = await consultar_fase(fase1, loop, executor)

    if not hallazgos1:
        return models.ResultadoBloque(bloque=str(sub_bloque), resultado="LIMPIO")

    # Fase 2: 10 IPs más
    fase1_set = set(fase1)
    restantes = [ip for ip in hosts if ip not in fase1_set]
    fase2 = restantes[:10]
    hallazgos2 = await consultar_fase(fase2, loop, executor)
>>>>>>> 26edf28 (Mejoras de legibilidad)

    if not hallazgos2:
        return models.ResultadoBloque(
            bloque=str(sub_bloque),
            resultado="AUDITORIA",
            hallazgos=hallazgos1
        )

<<<<<<< HEAD
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
=======
    # Fase 3: 11 IPs más
    fase2_set = set(fase2)
    restantes = [ip for ip in restantes if ip not in fase2_set]
    fase3 = restantes[:11]
    hallazgos3 = await consultar_fase(fase3, loop, executor)

    todos = hallazgos1 + hallazgos2 + hallazgos3

    if hallazgos3:
        return models.ResultadoBloque(
            bloque=str(sub_bloque), resultado="BLOQUEO", hallazgos=todos)

    return models.ResultadoBloque(
        bloque=str(sub_bloque), resultado="AUDITORIA", hallazgos=todos)


def evaluar_muestra(hallazgos, sub_bloque):
>>>>>>> 26edf28 (Mejoras de legibilidad)
    """
    Responsabilidad única: decidir LIMPIO vs AUDITORIA según los hallazgos.
    No es async porque no hace ningún I/O — solo evalúa datos ya obtenidos.
    """
    if not hallazgos:
        return models.ResultadoBloque(bloque=str(sub_bloque), resultado="LIMPIO")

    return models.ResultadoBloque(
        bloque=str(sub_bloque), resultado="AUDITORIA", hallazgos=hallazgos)


async def analizar_sub_bloques(sub_bloque, loop, executor, analisis_fases):
    if analisis_fases:
        return await analizar_por_fases(sub_bloque, loop, executor)

    sub_bloque_base = ipaddress.ip_network(sub_bloque, strict=False)
<<<<<<< HEAD

    # RN-06: análisis por fases
    if analisis_fases:
        return await analizar_por_fases(sub_bloque, loop, executor)

    # RN-04 y RN-05: muestreo simple
=======
>>>>>>> 26edf28 (Mejoras de legibilidad)
    muestra = obtener_muestra(sub_bloque_base)
    resultados_muestra = await consultar_fase(muestra, loop, executor)

<<<<<<< HEAD
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
=======
    return evaluar_muestra(resultados_muestra, sub_bloque)


async def procesar_sub_bloques(sub_bloques):
    loop = asyncio.get_running_loop()
>>>>>>> 26edf28 (Mejoras de legibilidad)
    executor = ThreadPoolExecutor(max_workers=constantes.MAX_WORKERS)

    try:
        logging.info("Iniciando análisis de sub-bloques")

        tareas = [
<<<<<<< HEAD
            analizar_sub_bloques(sub_bloque, loop, executor, analisis_fases)
            for sub_bloque, analisis_fases in sub_bloques
        ]

        resultados = await asyncio.wait_for(
            asyncio.gather(*tareas),
            timeout=300
        )
=======
            analizar_sub_bloques(sb, loop, executor, af)
            for sb, af in sub_bloques
        ]
        logging.info(
            f"Procesando lote de {len(sub_bloques)} sub-bloques"
        )

        resultados = await asyncio.wait_for(
            asyncio.gather(*tareas), timeout=1800)
>>>>>>> 26edf28 (Mejoras de legibilidad)

        reporte = {}
        for datos in resultados:
            reporte[datos.bloque] = {
<<<<<<< HEAD
                "ips":       datos.hallazgos,
                "resultado": datos.resultado
            }

=======
                "ips": datos.hallazgos,
                "resultado": datos.resultado
            }
>>>>>>> 26edf28 (Mejoras de legibilidad)
        logging.info("Análisis de sub-bloques terminado")
        return reporte

    finally:
        try:
            await loop.run_in_executor(None, executor.shutdown, True)
        except (ValueError, RuntimeError) as e:
            logging.error(f"Error cerrando executor: {e}")

<<<<<<< HEAD

=======
>>>>>>> 26edf28 (Mejoras de legibilidad)

def dividir_bloque(bloque):
    bloque_base = ipaddress.ip_network(bloque, strict=False)
    prefijo = bloque_base.prefixlen

    if prefijo < 16:
        raise ValueError(
            f"Segmento no soportado: /{prefijo}. Solo se aceptan /16 a /32")

    if 16 <= prefijo <= 23:
        return [(str(sub), True)
                for sub in bloque_base.subnets(new_prefix=24)]

    return [(str(bloque_base), False)]


def dividir_en_lotes(lista, tamano_lote=20):
    """
<<<<<<< HEAD
    Divide el bloque en sub-bloques y determina el tipo de análisis.

    Returns:
        list de tuplas: [(sub_bloque_str, analisis_fases), ...]

    Raises:
        ValueError: si el prefijo es menor a /16 (RN-07)
    """
=======
    Divide una lista en grupos para evitar lanzar cientos
    de tareas simultáneas cuando se analiza un /16.
    """
    for i in range(0, len(lista), tamano_lote):
        yield lista[i:i + tamano_lote]
>>>>>>> 26edf28 (Mejoras de legibilidad)

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

<<<<<<< HEAD

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
=======
async def procesar_bloque(bloque):
    """
    Responsabilidad única: dividir un bloque, procesarlo en lotes y
    devolver su resultado como dict. No maneja excepciones de negocio,
    eso lo hace el llamador (iniciar_blacklist).
    """
    sub_bloques = dividir_bloque(bloque)

    logging.info(
        f"Bloque {bloque} dividido en {len(sub_bloques)} sub-bloques"
    )

    resultado_final = {}
    for lote in dividir_en_lotes(sub_bloques, 20):
        respuesta = await procesar_sub_bloques(lote)
        if respuesta:
            resultado_final.update(respuesta)

    return {"bloques": resultado_final}


async def iniciar_blacklist(bloques):
    resultados = {}

    for bloque in bloques:
        try:
            resultados[str(bloque)] = await procesar_bloque(bloque)
>>>>>>> 26edf28 (Mejoras de legibilidad)

        except ValueError as e:
            logging.error(f"Bloque rechazado {bloque}: {e}")
            resultados[str(bloque)] = {"error": str(e)}

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
<<<<<<< HEAD
            logging.error(f"Error procesando {bloque}: {e}")
            resultados[str(bloque)] = {"error": str(e)}

    guardar_en_mongo(resultados)

=======
            logging.exception(e)
            resultados[str(bloque)] = {"error": str(e)}

    guardar_en_mongo(resultados)
>>>>>>> 26edf28 (Mejoras de legibilidad)
    return resultados