import sys
import asyncio
import ipaddress
from concurrent.futures import ThreadPoolExecutor

sys.path.append("/home/ngsop/lilaApp/plugins/utilidadesPlugins")
from loggingConfig import LoggerFileConfig
from constantesPlugins import LOG_CONFIG_FILES

from constants.constants import Constants
from models.models import ResultadoBloque
from utils import utils

logger = LoggerFileConfig().crearLogFile(LOG_CONFIG_FILES.get("blacklist_check"))


def obtener_bloques_a_procesar(bloques_directos):
    """
    Decide la fuente de los bloques a analizar (parámetro directo o cola de MongoDB).
    Returns:
        tuple: (id_doc, bloques, es_programada)
    """
    if bloques_directos:
        logger.info(f"Argumentos recibidos por parámetro: {bloques_directos}")
        return None, bloques_directos, False

    logger.info("Sin argumentos directos — Consultando base de datos por tareas programadas...")
    id_doc, bloques = utils.obtener_subredes_de_mongo()
    return id_doc, bloques, True


def notificar_resultado_programada(es_programada, id_doc):
    """
    Si la tarea proviene de Mongo, actualiza su estado para la gestión posterior en Java.
    """
    if es_programada and id_doc:
        utils.actualizar_estado_ejecutado(id_doc)
        logger.info(
            f"Estado actualizado para ID {id_doc} — Java enviará el correo en los próximos 60 segundos."
        )


def obtener_ips_muestra(sub_bloque):
    """Obtiene la muestra representativa de IPs a consultar."""
    prefijo = sub_bloque.prefixlen

    if 29 <= prefijo <= 32:
        return list(sub_bloque.hosts())

    if 24 <= prefijo <= 28:
        hosts = list(sub_bloque.hosts())
        if len(hosts) <= 4:
            return hosts

        if prefijo == 24:
            offsets = [12, 38, 64, 90, 116, 142, 168, 194, 220, 246]
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
    tareas = [
        loop.run_in_executor(executor, utils.consultar_ip_en_blacklist, str(ip))
        for ip in ips
    ]
    resultados = await asyncio.gather(*tareas)
    return [r for r in resultados if r is not None]


async def analizar_por_fases(sub_bloque, loop, executor):
    red = ipaddress.ip_network(sub_bloque, strict=False)
    hosts = list(red.hosts())

    # Fase 1
    fase1 = obtener_ips_muestra(red)
    hallazgos1 = await consultar_fase(fase1, loop, executor)
    if not hallazgos1:
        return ResultadoBloque(bloque=str(sub_bloque), resultado="LIMPIO")

    # Fase 2
    restantes = [ip for ip in hosts if ip not in set(fase1)]
    fase2 = restantes[:10]
    hallazgos2 = await consultar_fase(fase2, loop, executor)
    if not hallazgos2:
        return ResultadoBloque(bloque=str(sub_bloque), resultado="AUDITORIA", hallazgos=hallazgos1)

    # Fase 3
    restantes = [ip for ip in restantes if ip not in set(fase2)]
    fase3 = restantes[:11]
    hallazgos3 = await consultar_fase(fase3, loop, executor)

    todos = hallazgos1 + hallazgos2 + hallazgos3
    resultado_str = "BLOQUEO" if hallazgos3 else "AUDITORIA"
    return ResultadoBloque(bloque=str(sub_bloque), resultado=resultado_str, hallazgos=todos)


async def analizar_sub_bloque(sub_bloque, loop, executor, analisis_fases):
    if analisis_fases:
        return await analizar_por_fases(sub_bloque, loop, executor)

    sub_bloque_base = ipaddress.ip_network(sub_bloque, strict=False)
    muestra = obtener_ips_muestra(sub_bloque_base)
    resultados_muestra = await consultar_fase(muestra, loop, executor)

    if not resultados_muestra:
        return ResultadoBloque(bloque=str(sub_bloque), resultado="LIMPIO")
    return ResultadoBloque(bloque=str(sub_bloque), resultado="AUDITORIA", hallazgos=resultados_muestra)


async def procesar_sub_bloques(sub_bloques):
    loop = asyncio.get_running_loop()
    executor = ThreadPoolExecutor(max_workers=Constants.MAX_WORKERS)

    try:
        tareas = [
            analizar_sub_bloque(sb, loop, executor, fases)
            for sb, fases in sub_bloques
        ]
        resultados = await asyncio.wait_for(asyncio.gather(*tareas), timeout=1800)

        reporte = {}
        for r in resultados:
            reporte[r.bloque] = {"ips": r.hallazgos, "resultado": r.resultado}
        return reporte
    finally:
        executor.shutdown(wait=True)


def dividir_bloque(bloque):
    bloque_base = ipaddress.ip_network(bloque, strict=False)
    prefijo = bloque_base.prefixlen

    if prefijo < 16:
        raise ValueError(f"Segmento no soportado: /{prefijo}. Solo se aceptan /16 a /32")

    if 16 <= prefijo <= 23:
        return [(str(sub), True) for sub in bloque_base.subnets(new_prefix=24)]

    return [(str(bloque_base), False)]


def dividir_en_lotes(lista, tamano_lote=20):
    for i in range(0, len(lista), tamano_lote):
        yield lista[i:i + tamano_lote]


async def procesar_bloque(bloque):
    sub_bloques = dividir_bloque(bloque)
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
        except Exception as e:
            logger.error(f"Error procesando bloque {bloque}: {e}")
            resultados[str(bloque)] = {"error": str(e)}
    return resultados


def principal(bloques_directos=None):
    """
    Método de entrada unificado invocado por main.py.
    """
    logger.info("=== Iniciando ejecución del Plugin Blacklist ===")

    id_doc, bloques, es_programada = obtener_bloques_a_procesar(bloques_directos)

    if not bloques:
        logger.error("No hay bloques que analizar — Abortando ejecución.")
        return {"status": "NO_WORK"}

    logger.info(f"Iniciando análisis de {len(bloques)} bloque(s): {bloques}")

    respuesta = asyncio.run(iniciar_blacklist(bloques))

    if not respuesta:
        logger.error("El análisis no retornó resultados válidos.")
        return {"status": "FAILED"}

    logger.info("Análisis completado correctamente.")
    notificar_resultado_programada(es_programada, id_doc)

    print(respuesta)
    return {"status": "SUCCESS", "data": respuesta}