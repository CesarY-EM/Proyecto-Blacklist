## sys.path.append("/home/ngsop/lilaApp/plugins/utilidadesPlugins")
##from loggingConfig import LoggerFileConfig
##from constantesPlugins import LOG_CONFIG_FILES
##logging = LoggerFileConfig().crearLogFile(LOG_CONFIG_FILES.get("blacklist_check"))

# Tiempo
import time

# Archivos de texto
import os
from ipaddress import IPv4Network


#from fastapi import FastAPI, HTTPException

async def consultar(bloque):
    """Recibe lista de direcciones ip y devuelve JSON """

    ##providers = BASE_PROVIDERS + [Provider('truncate.gbudb.net'),Provider('spam.spamrats.com'),Provider('dyna.spamrats.com'),Provider('auth.spamrats.com'),Provider('noptr.spamrats.com')]
    #subredes = blacklist.netsInput

    # obtiene arreglo de ips
    ipps = desglosar_direcciones_ip(bloque)
    logging.info("Desglose de direcciones ip exitoso")

    # Ejecución multihilo de consulta(se reparten las ip a 4 hilos)
    # Sólo se consultan 4000 direcciones para realizar pruebas más fluidas
    ips_blacked = consultar_blacklist_thread(ipps, providers, 20)

    
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor(max_workers=10) as executor:
        tareas = [
            loop.run_in_executor(executor, verificar_ip, str(ip), providers)
            for ip in ips
        ]
        resultados = await asyncio.gather(*tareas)
    
    marcadas = [r for r in resultados if r is not None]
    

    logging.info("Ejecución multithread exitosa ")

    count_prov = obtener_proveedores(ips_blacked)


    # Generar CSV
    ##csv_string=generar_CSV_string(count_prov, ips_blacked)
    ##logging.info(csv_string)

    # Generar JSON
    ##respuesta_JSON = generar_JSON(count_prov, ips_blacked)
    ##respuesta_JSON["reporte_csv"]=csv_string

    return respuesta_JSON


from ipaddress import IPv4Network

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


def medir_tiempo(respuesta_json, num_ips, tiempo, hilos=1):
    respuesta_json["num_dir"] = num_ips
    respuesta_json["tiempo"] = tiempo
    respuesta_json["hilos"] = hilos




def verificar_ip(ip, providers = None):
    checker = DNSBLIpChecker(providers=providers)
    resultado = checker.check(ip)

    if resultado.blacklisted:
        return {
            "ip": ip,
            "dominios": ", ".join(resultado.detected_by.keys())
        }
    return None

def consultar_blacklist_thread(ipps, providers, numthreads=4):
    """Reparte direcciones ip a N hilos y espera terminación de todos para devolver respuesta
    Mejora: Considerar repartición de providers y modificación de algoritmo"""
    logging.info("Iniciando generador de hilos")
    arreglo_hilos = []

    # Número de ips por hilo
    if (len(ipps) < 4):
        logging.info("Sólo se utilizará un hilo")

    num_ip = len(ipps)//numthreads

    # Creamos N hilos, por default 4
    for i in range(numthreads):
        arreglo_hilos.append(BulkThread(
            ipps[i*num_ip:(i+1)*num_ip], providers))
    

    # Iniciamos todos los hilos
    [hilo.start() for hilo in arreglo_hilos]

    # Esperamos a todos los hilos
    [hilo.join() for hilo in arreglo_hilos]

    # Unimos resultados parciales
    results = []
    #results += [hilo.resultado for hilo in arreglo_hilos]
    # Unimos resultados parciales
    results = []
    for hilo in arreglo_hilos:
        results += hilo.resultado

    # Sólo guardamos direcciones ip en blacklist
    ip_blacked = []
    ip_blacked += [x for x in results if x.blacklisted]
    return ip_blacked


def consultar_blacklist(ipps, providers):
    """Se consultan de forma asíncrona varias ip"""
    checker = DNSBLIpChecker(providers=providers)
    ip_blacked = []
    results = checker.bulk_check(ipps)  # Resultado de todas las ip
    ip_blacked += [x for x in results if x.blacklisted]
    return ip_blacked


def desglosar_direcciones_ip(ips):
    """Recibe arreglo de subredes en formato CIDR y devuelve todas las ip correspondientes"""
    ipps = list(ips.hosts())

    return ipps


def obtener_proveedores(resultados):
    """Se busca cuales proveedores encontraron direcciones en blacklist y se devuelve un diccionario con la cuenta"""

    logging.info("Inciando obtención de proveedores")
    prov = []
    for i in resultados:
        prov += list(i.detected_by.keys())
    count_prov = Counter(prov)  # {proveedora: m, proveedorb: n}
    logging.info("Obtención de proveedores exitosa")
    return count_prov


def comprobar_errores_servicio(resultados):
    """Permite analizar resultados para contar proveedores que dieron error
    
    Podría usarse para detectar proveedores con menor tasa de errores y priorizarlos durante ejecución multihilo """
    file = open("errores_servicio.txt", "w")

    for i in resultados:
        file.write("DIRECCION con  "+str(len(i.failed_providers)) + " errores en proveedor"+os.linesep)
    file.close()


def generar_CSV(nombre_archivo, count_prov, ips_blacked):
    """Genera CSV con direcciones ip en black list y proveedores correspondientes(x significa que 
    la ip está en blacklist de acuerdo al proveedor, -  significa que no lo está)"""

    try:

        with open(nombre_archivo, 'a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(["IP"] + list(count_prov.keys()))
            for blacklisted in ips_blacked:
                # Dirección, listas negras
                row = []
                for p in count_prov.keys():  # Para cada proveedor
                    if p in list(blacklisted.detected_by.keys()):
                        row.append("x")

                    else:
                        row.append("-")
                writer.writerow([blacklisted.addr] + row)
        logging.info("Generación de CSV exitosa")
        return True
    except:
        logging.error("Error al generar CSV")
        return False
    
    
def generar_CSV_string(count_prov, ips_blacked):
    """Genera una cadena CSV con direcciones IP en blacklist y proveedores correspondientes
    (x significa que la IP está en blacklist de acuerdo al proveedor, - significa que no lo está)"""

    try:
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(["IP"] + list(count_prov.keys()))
        for blacklisted in ips_blacked:
            # Dirección, listas negras
            row = []
            for p in count_prov.keys():  # Para cada proveedor
                if p in list(blacklisted.detected_by.keys()):
                    row.append("x")
                else:
                    row.append("-")
            writer.writerow([blacklisted.addr] + row)
        
        logging.info("Generación de CSV exitosa")
        return output.getvalue()
    except Exception as e:
        logging.error(f"Error al generar CSV: {e}")
        return None




def generar_JSON(count_prov, ips_blacked):
    """Recibe lista de PYDNS_ip_blacked y devuelve resultados formateados"""

    diccionario_proveedores = {}

    for proveedor_actual in count_prov.keys():
        diccionario_proveedores[proveedor_actual] = []

    for blacklisted in ips_blacked:
        for p in count_prov.keys():
            if p in list(blacklisted.detected_by.keys()):
                diccionario_proveedores[p].append(blacklisted.addr)

    respuesta_json = {"reporte": []}

    # Para cada proveedor se crea un objeto con el nombre y su respectivo arreglo de ips

    for proveedor_actual in diccionario_proveedores:  # Para cada proveedor dentro del diccionario
        respuesta_json["reporte"].append(
            {
                "proveedor": proveedor_actual,
                "blacked": diccionario_proveedores[proveedor_actual]
            }
        )
    return respuesta_json
