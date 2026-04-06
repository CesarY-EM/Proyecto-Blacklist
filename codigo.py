import os 
import ipaddress
import asyncio
import threading
import json

from concurrent.futures import ThreadPoolExecutor
from pydnsbl import DNSBLIpChecker
from ipaddress import IPv4Network
from datetime import datetime


def validar_bloques(bloques):
    validos = []
    invalidos = []

    for bloque in bloques:
        try:
            red = IPv4Network(bloque.strip(), strict=False)
            validos.append(red)
        except ValueError as e:
            invalidos.append({"bloque": bloque.strip(), "error": str(e)})

    return validos

def verificar_ip(ip, providers = None):
    checker = DNSBLIpChecker(providers=providers) if providers else DNSBLIpChecker()
    resultado = checker.check(ip)

    if resultado.blacklisted:
        return {
            "ip": ip,
            "dominios": ", ".join(resultado.detected_by.keys())
        }
    return None

def desglosar_direcciones_ip(ips):
    red = ipaddress.ip_network(ips, strict=False)
    ipps = list(red.hosts())
    return ipps

async def consultar(bloque):

    ipps = desglosar_direcciones_ip(bloque)
    
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor(max_workers=10) as executor:
        tareas = [
            loop.run_in_executor(executor, verificar_ip, str(ip)) ##Aqui agregariamos los providers que queramos
            for ip in ipps
        ]
        resultados = await asyncio.gather(*tareas)
    
    marcadas = [r for r in resultados if r is not None]

    if marcadas:
        try:
            nombre = f"resultado_{datetime.now().strftime('%d%m%Y')}.json"
            with open(nombre, "w", encoding="utf-8") as f:
                json.dump(marcadas, f, indent=4)
            print("\nGuardado en resultado.json")
        except PermissionError:
            print("\n⚠ No se pudo generar el archivo")

        return True
    else:
        return False
