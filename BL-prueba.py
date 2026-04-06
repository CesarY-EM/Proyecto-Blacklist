
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
       #logging.info("Generación de CSV exitosa")
       return True
   except:
       #logging.error("Error al generar CSV")
       return False




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
