import asyncio
from concurrent.futures import ThreadPoolExecutor
from pydnsbl import DNSBLIpChecker
import ipaddress
import csv
import os
import ipaddress
import threading
import json
import csv

from datetime import datetime, timedelta
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from pydnsbl import DNSBLIpChecker
from ipaddress import IPv4Network
from datetime import datetime

CACHE_FILE = "cache.csv"
CACHE_EXPIRACION = 7
MAX_WORKERS = 10


def cargar_cache():
    """Lee el archivo de caché y devuelve un diccionario {ip: {datos}}"""
    cache = {}
    if not Path(CACHE_FILE).exists():
        return cache

    with open(CACHE_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cache[row["ip"]] = {
                "blacklisted": row["blacklisted"] == "True",
                "dominios": row["dominios"],
                "fecha_consulta": datetime.strptime(row["fecha_consulta"], "%d-%m-%Y")
            }
    return cache

def guardar_cache(cache):
    """Escribe el caché completo al archivo"""
    with open(CACHE_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["ip", "blacklisted", "dominios","fecha_consulta"])
        writer.writeheader()
        for ip, datos in cache.items():
            writer.writerow({
                "ip": ip,
                "blacklisted": datos["blacklisted"],
                "dominios": datos["dominios"],
                "fecha_consulta": datos["fecha_consulta"].strftime("%d-%m-%Y") if isinstance(datos["fecha_consulta"], datetime) else datos["fecha_consulta"]
            })

def ip_en_cache_valida(ip, cache):
    """Verifica si la IP está en caché y no ha expirado"""
    if ip not in cache:
        return False
    
    edad = datetime.now() - cache[ip]["fecha_consulta"]
    return edad < timedelta(days=CACHE_EXPIRACION)

def verificar_ip(ip,cache, providers = None):

    if ip_en_cache_valida(ip, cache):
            datos = cache[ip]
            return {
                "ip": ip,
                "dominios": datos["dominios"],
            } if datos["blacklisted"] else None

    checker = DNSBLIpChecker(providers=providers) if providers else DNSBLIpChecker()
    resultado = checker.check(ip)

    entrada_cache = {
        "blacklisted": resultado.blacklisted,
        "dominios": ", ".join(resultado.detected_by.keys()) if resultado.blacklisted else "",
        "fecha_consulta": datetime.now().strftime("%d-%m-%Y")
    }
    cache[ip] = entrada_cache

    if resultado.blacklisted:
        return {
            "ip": ip,
            "dominios": entrada_cache["dominios"]
        }
    return None

async def consultar(bloque):

    red = ipaddress.ip_network(bloque, strict=False)
    ips = list(red.hosts())


    print(f"Red: {red}")

    cache = cargar_cache()

    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        tareas = [
            loop.run_in_executor(executor, verificar_ip, str(ip), cache)
            for ip in ips
        ]
        resultados = await asyncio.gather(*tareas)

    guardar_cache(cache)

    marcadas = [r for r in resultados if r is not None]

    if marcadas:
        print("\nIPs en blacklist:")
        for item in marcadas:
            print(f"  {item['ip']} → {item['dominios']}")
    else:
        print("Ninguna IP marcada en blacklist.")

    if marcadas:
        nombre = f"resultado_{datetime.now().strftime('%d-%m-%Y_%H-%M-%S')}.csv"
        try:
            with open(nombre, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=["ip", "dominios", "categorias"])
                writer.writeheader()
                writer.writerows(marcadas)
                print("\nGuardado en resultado.csv")
                return True
        except PermissionError:
            print("\n⚠ No se pudo generar el archivo")
            return True
    else:
        return False

if __name__ == "__main__":
    asyncio.run(main())