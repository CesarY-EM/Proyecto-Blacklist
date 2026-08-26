import sys
import asyncio
import ipaddress
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any, Optional

sys.path.append("/home/ngsop/lilaApp/plugins/utilidadesPlugins")
from loggingConfig import LoggerFileConfig
from constantesPlugins import LOG_CONFIG_FILES

from constants.constantes import Constants
from models.models import ResultadoBloque
from utils.DNSBL_utils import consultar_ip_en_blacklist
from business.business_mongo import obtener_bloques_a_procesar, notificar_resultado_programada
from utils.Validadores_utils import is_valid

logger = LoggerFileConfig().crearLogFile(LOG_CONFIG_FILES.get("blacklist_check"))


def obtener_ips_muestra(sub_bloque: ipaddress.IPv4Network) -> List[ipaddress.IPv4Address]:
    """Obtiene la muestra representativa de IPs a consultar usando Constants."""
    prefijo = sub_bloque.prefixlen

    # Bloques pequeños (/29 a /32)
    if Constants.PREFIJO_MIN_PEQUENO <= prefijo <= Constants.PREFIJO_MAX_PEQUENO:
        return list(sub_bloque.hosts())

   
    if Constants.PREFIJO_24 <= prefijo < Constants.PREFIJO_MIN_PEQUENO:
        hosts = list(sub_bloque.hosts())
        if len(hosts) <= 4:
            return hosts

       
        if prefijo == Constants.PREFIJO_24:
            muestra = []
            for offset in Constants.OFFSETS_FASE1_PREFIJO_24:
                ip = sub_bloque.network_address + offset
                if ip in sub_bloque and ip != sub_bloque.broadcast_address:
                    muestra.append(ip)
            return muestra

        
        posiciones = [
            (len(hosts) * factor) // Constants.DIVISOR_PROPORCIONAL
            for factor in Constants.FACTORES_PROPORCIONALES
        ]
        return [hosts[pos] for pos in posiciones]

    return []


async def consultar_fase(ips: List[ipaddress.IPv4Address], loop: asyncio.AbstractEventLoop, executor: ThreadPoolExecutor) -> List[Dict[str, Any]]:
    tareas = [
        loop.run_in_executor(executor, consultar_ip_en_blacklist, str(ip))
        for ip in ips
    ]
    resultados = await asyncio.gather(*tareas)
    return [r for r in resultados if r is not None]


async def analizar_por_fases(sub_bloque: str, loop: asyncio.AbstractEventLoop, executor: ThreadPoolExecutor) -> ResultadoBloque:
    red = ipaddress.ip_network(sub_bloque, strict=False)
    hosts = list(red.hosts())

    # Fase 1: Muestreo Rápido
    fase1 = obtener_ips_muestra(red)
    hallazgos1 = await consultar_fase(fase1, loop, executor)
    if not hallazgos1:
        return ResultadoBloque(bloque=str(sub_bloque), resultado="LIMPIO")

    # Fase 2: Muestreo Intermedio
    restantes = [ip for ip in hosts if ip not in set(fase1)]
    fase2 = restantes[:10]
    hallazgos2 = await consultar_fase(fase2, loop, executor)
    if not hallazgos2:
        return ResultadoBloque(bloque=str(sub_bloque), resultado="AUDITORIA", hallazgos=hallazgos1)

    # Fase 3: Evaluación Completa
    restantes = [ip for ip in restantes if ip not in set(fase2)]
    fase3 = restantes[:11]
    hallazgos3 = await consultar_fase(fase3, loop, executor)

    todos = hallazgos1 + hallazgos2 + hallazgos3
    resultado_str = "BLOQUEO" if hallazgos3 else "AUDITORIA"
    return ResultadoBloque(bloque=str(sub_bloque), resultado=resultado_str, hallazgos=todos)


async def analizar_sub_bloque(sub_bloque: str, loop: asyncio.AbstractEventLoop, executor: ThreadPoolExecutor, analisis_fases: bool) -> ResultadoBloque:
    if analisis_fases:
        return await analizar_por_fases(sub_bloque, loop, executor)

    sub_bloque_base = ipaddress.ip_network(sub_bloque, strict=False)
    muestra = obtener_ips_muestra(sub_bloque_base)
    resultados_muestra = await consultar_fase(muestra, loop, executor)

    if not resultados_muestra:
        return ResultadoBloque(bloque=str(sub_bloque), resultado="LIMPIO")
    return ResultadoBloque(bloque=str(sub_bloque), resultado="AUDITORIA", hallazgos=resultados_muestra)


async def procesar_sub_bloques(sub_bloques: List[tuple]) -> Dict[str, Any]:
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


def dividir_bloque(bloque: str) -> List[tuple]:
    bloque_base = ipaddress.ip_network(bloque, strict=False)
    prefijo = bloque_base.prefixlen

    if prefijo < Constants.PREFIJO_16:
        raise ValueError(f"Segmento no soportado: /{prefijo}. Solo se aceptan /{Constants.PREFIJO_16} a /{Constants.PREFIJO_MAX_PEQUENO}")

    if Constants.PREFIJO_16 <= prefijo < Constants.PREFIJO_24:
        return [(str(sub), True) for sub in bloque_base.subnets(new_prefix=Constants.PREFIJO_24)]

    return [(str(bloque_base), False)]


def dividir_en_lotes(lista: list, tamano_lote: int = Constants.TAMANO_LOTE):
    for i in range(0, len(lista), tamano_lote):
        yield lista[i:i + tamano_lote]


async def procesar_bloque(bloque: str) -> Dict[str, Any]:
    sub_bloques = dividir_bloque(bloque)
    resultado_final = {}
    for lote in dividir_en_lotes(sub_bloques, 20):
        respuesta = await procesar_sub_bloques(lote)
        if respuesta:
            resultado_final.update(respuesta)
    return {"bloques": resultado_final}


async def iniciar_blacklist(bloques: List[str]) -> Dict[str, Any]:
    resultados = {}
    for bloque in bloques:
        try:
            resultados[str(bloque)] = await procesar_bloque(bloque)
        except Exception as e:
            logger.error(f"Error procesando bloque {bloque}: {e}")
            resultados[str(bloque)] = {"error": str(e)}
    return resultados


def principal(bloques_directos: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Método de entrada unificado invocado por main.py.
    """
    if not is_valid(bloques_directos):
        logger.error(f"Payload de entrada inválido: {bloques_directos}")
        return {
            "status": "ERROR",
            "message": "El payload de entrada es inválido. Se esperaba una lista con subredes/IPs válidas."
        }
    
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