import asyncio

from business.business import comprobar_subredes_blacklist

if __name__ == "__main__":

    bloques = ["200.67.0.0/24"]

    respuesta = asyncio.run(comprobar_subredes_blacklist(bloques))
    
    if respuesta is None:
        print("No se pudo completar el análisis")  