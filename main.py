import csv
import json
import asyncio
import ipaddress

from v2 import validar
from v2 import consultar

def generar_csv_reporte(reporte_maestro):
    nombre_archivo = "prueba_mixto.csv"

    todos_los_dominios = set()
    for datos in reporte_maestro.values():

        if datos["resultado"] == "AUDITORIA":
            for hallazgo in datos["ips"]:
                if hallazgo and isinstance(hallazgo["dominios"], str):
                    todos_los_dominios.update(hallazgo["dominios"].split(", "))

    columnas_dnsbl = sorted(todos_los_dominios)
    encabezados = ["Bloque", "IPs Muestra", "Resultado"] + columnas_dnsbl + ["Total Listas"]


    with open(nombre_archivo, mode="w", newline="", encoding="utf-8") as archivo:
        writer = csv.DictWriter(archivo, fieldnames=encabezados)
        writer.writeheader()

        for segmento, datos in reporte_maestro.items():
            resultado = datos["resultado"]
            ips_muestra = " | ".join(str(ip) for ip in datos["ips_muestreadas"])

            if resultado in ("LIMPIO", "BLOQUEO"):
                fila = {
                    "Bloque": segmento,
                    "IPs Muestra": ips_muestra,
                    "Resultado": resultado,
                    "Total Listas": len(datos["ips"]) if datos["ips"] else 0,
                }

                for dominio in columnas_dnsbl:
                    fila[dominio] = ""
                writer.writerow(fila)
                
            elif resultado == "AUDITORIA":

                if not datos["ips"]:
                    writer.writerow({
                        "Bloque": segmento,
                        "IPs Muestra": "",
                        "Resultado": resultado,
                        "Total Listas": 0,
                        **{d: "" for d in columnas_dnsbl},
                    })
                    continue

                for h in datos["ips"]:
                    if not h:
                        continue
                
                    ip_str = str(h["ip"]) if not isinstance(h["ip"], str) else h["ip"]
                    
                    fila = {
                        "Bloque": segmento,
                        "IPs Muestra": ip_str,
                        "Resultado": resultado,
                    }

                    conteo = 0

                    for dominio in columnas_dnsbl:
                        if dominio in h["dominios"]:
                            fila[dominio] = 1
                            conteo += 1
                        else:
                            fila[dominio] = 0

                    fila["Total Listas"] = conteo
                    writer.writerow(fila)


def dividir_bloque(red, prefijo=24):

    red = ipaddress.ip_network(red, strict=False)

    if red.prefixlen >= prefijo:
        return [red]

    return list(red.subnets(new_prefix=prefijo))


async def comprobar_subredes_blacklist(subredes):

    """
    Funcion principal, es el "orquestador"

    Args:
        None: Subredes a validar y sub dividir

    Returns:
        string: None
    """

    respuesta = False
    validos = validar([subredes])

    if not validos:
        print("error: Direcciones no validas")
        return

    bloques = dividir_bloque(subredes)
    for bloque in bloques:
        print(bloque)

    try:
        respuesta = await consultar(bloques)
    except Exception as e:
        print(f"error:Error consultar -  {e}")
        return None
    
    if respuesta is None:
        print("error: consultar no devolvio resultados")
        return None
    
    print("--- Generando reporte final ---")
    generar_csv_reporte(respuesta)
    
    return respuesta
        

if __name__ == "__main__":
    respuesta = asyncio.run(comprobar_subredes_blacklist("185.220.101.0/18"))
    
    if respuesta is None:
        print("No se pudo completar el análisis")   
