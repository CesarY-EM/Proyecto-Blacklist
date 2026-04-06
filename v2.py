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
UMBRAL = 1.0
TAMANO_MUESTRA = 13


def get_checker():
    if not hasattr(_local, "checker"):
        _local.checker = DNSBLIpChecker(timeout=2)
    return _local.checker


def validar(bloques):
    validos = []
    invalidos = []

    for bloque in bloques:
        try:
            red = IPv4Network(bloque.strip(), strict=False)
            validos.append(red)
        except ValueError as e:
            invalidos.append({"bloque": bloque.strip(), "error": str(e)})

    return validos


def generar_reporte(resultados: list[dict], archivo: str = None):
    if archivo is None:
        archivo = f"reporte_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    with open(archivo, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        # ── Sección 1: bloques con predicción ──────────────────────────────
        writer.writerow(["# BLOQUES CON PREDICCION DE LISTADO COMPLETO"])
        writer.writerow(["red", "confianza", "ips_muestra", "dominios_encontrados"])

        for r in resultados:
            if not r["prediccion"]:
                continue

            dominios = set()
            for hit in r["hits_muestra"]:
                dominios.update(hit["dominios"].split(", "))

            writer.writerow(
                [
                    r["red"],
                    f"{r['confianza']:.0%}",
                    " | ".join(r["ips_muestra"]),
                    " | ".join(sorted(dominios)),
                ]
            )

        writer.writerow([])  # línea vacía entre secciones

        # ── Sección 2: bloques analizados completamente ────────────────────
        writer.writerow(["# BLOQUES ANALIZADOS COMPLETAMENTE"])
        writer.writerow(["red", "ip_listada", "dominios"])

        for r in resultados:
            if r["prediccion"]:
                continue
            if not r["hits_completos"]:
                continue

            for hit in r["hits_completos"]:
                writer.writerow(
                    [
                        r["red"],
                        hit["ip"],
                        hit["dominios"],
                    ]
                )

    print(f"Reporte generado: {archivo}")
    return archivo


def verificar_ip(ip, providers=None):
    try:
        checker = get_checker()
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
    
    positivos = [r for r in resultados_muestra if r is not None]
    conteo_positivos = len(positivos)
    

    porcentaje = conteo_positivos / total_muestra
    
    if porcentaje >= UMBRAL:
        return "BLOQUEO"
        
    if conteo_positivos == 0:
        return "LIMPIO"
        
    return "AUDITORIA"


async def analizar_bloque(bloque, loop, executor):
    red = ipaddress.ip_network(bloque, strict=False)
    todas = list(red.hosts())

    if len(todas) <= TAMANO_MUESTRA:
        muestra = todas[:]
    else:
        primera = todas[0]
        ultima = todas[-1]
        # Excluir primera y última para el muestreo central
        centro = [ip for ip in todas if ip not in (primera, ultima)]
        centro_aleatorio = random.sample(centro, 13)
        muestra = [primera] + centro_aleatorio + [ultima]

    verificar_muestra = [
        loop.run_in_executor(executor, verificar_ip, str(ip)) for ip in muestra
    ]
    resultados_muestra = await asyncio.gather(*verificar_muestra)
    resultado = evaluar(resultados_muestra, len(muestra))
    hallazgos = [r for r in resultados_muestra if r is not None]

    # Guardar muestra siempre como strings
    muestra_str = [str(ip) for ip in muestra]

    if resultado == "BLOQUEO":
        print(f"[+] [ok] {bloque} terminado")
        return {
            "bloque": str(bloque),
            "hallazgos": hallazgos,
            "muestras": muestra_str,
            "resultado": "BLOQUEO",
        }

    elif resultado == "LIMPIO":
        print(f"[+] [ok] {bloque} terminado")
        return {
            "bloque": str(bloque),
            "hallazgos": hallazgos,
            "muestras": muestra_str,
            "resultado": "LIMPIO",
        }

    else:
        # AUDITORIA — consultar todas las IPs que no estaban en la muestra
        muestra_set = set(muestra_str)
        restantes = [ip for ip in todas if str(ip) not in muestra_set]

        buscar_hallazgos = [
            loop.run_in_executor(executor, verificar_ip, str(ip)) for ip in restantes
        ]
        resultados = await asyncio.gather(*buscar_hallazgos)
        hallazgos = [r for r in resultados if r is not None]

        print(f"[+] [ok] {bloque} terminado")
        return {
            "bloque": str(bloque),
            "hallazgos": hallazgos,
            "muestras": muestra_str,
            "resultado": "AUDITORIA",
        }

async def consultar(bloques):
    loop = asyncio.get_running_loop() 
    executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)
    
    try:
        print(">>> Iniciando análisis asíncrono...")
        tareas = [analizar_bloque(b, loop, executor) for b in bloques]
        resultados = await asyncio.gather(*tareas)
        
        reporte = {}
        for r in resultados:
            bloque = r["bloque"]
            reporte[bloque] = { "ips" : r["hallazgos"],
                                "ips_muestreadas": [str(ip) for ip in r["muestras"]], 
                                "resultado": r["resultado"]
                                }
        
        return reporte
    finally:
        try:
            await loop.run_in_executor(None, executor.shutdown, True)
        except ValueError:
            pass
        
        
'''
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        tareas = [analizar_bloque(bloque, loop, executor) for bloque in bloques]
        resultados = await asyncio.gather(*tareas)
        
    for r in resultados:
        bloque = r["bloque"]
        reporte[bloque] = { "ips" : r["hallazgos"],
                            "ips_muestreadas" : r["muestras"],
                            "resultado": r["resultado"]
                            }

    generar_csv_reporte(reporte)
    return True
    
'''