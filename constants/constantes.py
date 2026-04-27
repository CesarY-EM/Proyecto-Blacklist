from pydnsbl.providers import Provider

MAX_WORKERS = 20
UMBRAL = 0.8

MUESTRA_24 = 25
MUESTRA_16 = 100

PREFIJO_24 = 24
PREFIJO_16 = 16

PROVIDERS = [Provider('truncate.gbudb.net'),
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