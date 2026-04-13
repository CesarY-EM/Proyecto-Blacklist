import json
import asyncio
import ipaddress

from openpyxl import Workbook
from openpyxl.styles import PatternFill, Font

from funcionalidades import validar
from funcionalidades import consultar

def generar_excel_reporte(reporte_maestro):
    nombre_archivo = f"reporte_prueba.xlsx"
    wb = Workbook()

    negrita = Font(bold=True)

    todos_los_dominios = set()
    for datos in reporte_maestro.values():
        if datos["resultado"] == "AUDITORIA":
            for h in datos["ips"]:
                if h and isinstance(h["dominios"], str):
                    todos_los_dominios.update(h["dominios"].split(", "))
    columnas_dnsbl = sorted(todos_los_dominios)

    # Pestaña BLOQUEO
    ws_bloqueo = wb.active
    ws_bloqueo.title = "BLOQUEO"
    ws_bloqueo.append(["Bloque", "Resultado"])
    for cell in ws_bloqueo[1]:
        cell.font = negrita

    for segmento, datos in reporte_maestro.items():
        if datos["resultado"] != "BLOQUEO":
            continue
        ws_bloqueo.append([segmento, "BLOQUEO"])

    # Pestaña LIMPIO
    ws_limpio = wb.create_sheet("LIMPIO")
    ws_limpio.append(["Bloque", "Resultado"])
    for cell in ws_limpio[1]:
        cell.font = negrita

    for segmento, datos in reporte_maestro.items():
        if datos["resultado"] != "LIMPIO":
            continue
        ws_limpio.append([segmento, "LIMPIO"])

    # ── Pestaña AUDITORIA ─────────────────────────────────────────────────
    ws_auditoria = wb.create_sheet("AUDITORIA")
    encabezados_auditoria = ["Bloque", "IP's", "resultado"] + columnas_dnsbl
    ws_auditoria.append(encabezados_auditoria)
    for cell in ws_auditoria[1]:
        cell.font = negrita

    for segmento, datos in reporte_maestro.items():
        if datos["resultado"] != "AUDITORIA":
            continue
        if not datos["ips"]:
            ws_auditoria.append([segmento, "N/A", "AUDITORIA"] + [""] * len(columnas_dnsbl) + [0])
            continue
        for h in datos["ips"]:
            if not h:
                continue
            conteo = 0
            cols = []
            for dominio in columnas_dnsbl:
                if dominio in h["dominios"]:
                    cols.append(1)
                    conteo += 1
                else:
                    cols.append(0)
            fila = [segmento, h["ip"], "AUDITORIA"] + cols + [conteo]
            ws_auditoria.append(fila)

    wb.save(nombre_archivo)
    print(f"✅ Reporte generado exitosamente: {nombre_archivo}")
    return nombre_archivo

def dividir_bloque(red, prefijo=24):

    red = ipaddress.ip_network(red, strict=False)

    if red.prefixlen >= prefijo:
        return [red]

    return list(red.subnets(new_prefix=prefijo))


async def comprobar_subredes_blacklist(subredes):

    """
    Funcion principal, es el "orquestador"

    Args:
        string: Subredes a validar y sub dividir

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
    generar_excel_reporte(respuesta)
    
    return respuesta
        

if __name__ == "__main__":
    respuesta = asyncio.run(comprobar_subredes_blacklist("1.1.1.0/22"))
    
    if respuesta is None:
        print("No se pudo completar el análisis")   
