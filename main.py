import sys
import json
from business.business_analisis import principal

def main():
    argumentos = sys.argv[1:]
    resultado = principal(argumentos)
    print(json.dumps(resultado, ensure_ascii=False))

if __name__ == "__main__":
    main()