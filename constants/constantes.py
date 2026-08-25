from pydnsbl.providers import Provider

class Constants:
    MAX_WORKERS = 20
    TAMANO_LOTE = 20  
    
    # Máscaras de subred
    PREFIJO_16 = 16
    PREFIJO_24 = 24
    PREFIJO_MIN_PEQUENO = 29
    PREFIJO_MAX_PEQUENO = 32

    # Configuración para muestreo de IPs
    OFFSETS_FASE1_PREFIJO_24 = [12, 38, 64, 90, 116, 142, 168, 194, 220, 246]
    FACTORES_PROPORCIONALES = [1, 2, 3, 4]
    DIVISOR_PROPORCIONAL = 5

    PROVIDERS = [
        Provider('truncate.gbudb.net'),
        Provider('spam.spamrats.com'),
        Provider('dyna.spamrats.com'),
        Provider('auth.spamrats.com'),
        Provider('noptr.spamrats.com'),
        Provider('zen.spamhaus.org'),
        Provider('bl.spamcop.net'),
        Provider('b.barracudacentral.org'),
        Provider('dnsbl.sorbs.net'),
    ]

    PESTANAS = {
        "BLOQUEO":   {"color": "FFB3B3", "columnas": ["Bloque", "Resultado"]},
        "LIMPIO":    {"color": "B3FFB3", "columnas": ["Bloque", "Resultado"]},
        "AUDITORIA": {"color": "FFD9B3", "columnas": ["Bloque", "IP", "Resultado"]},
    }