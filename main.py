import sys
import json

sys.path.append("/home/ngsop/lilaApp/plugins/utilidadesPlugins")
from business.business import ejecutar

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Decodificamos el JSON que viene en sys.argv[1]
        lista_bloques = json.loads(sys.argv[1])
        ejecutar(bloques_directos=lista_bloques)
    else:
        ejecutar()