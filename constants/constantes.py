from pydnsbl.providers import Provider


MAX_WORKERS = 50
TIMEOUT = 2
UMBRAL = 0.8

MUESTRA_24 = 25
MUESTRA_16 = 100

PREFIJO_24 = 24
PREFIJO_16 = 16

PROVIDERS = [Provider('truncate.gbudb.net'),
                       Provider('spam.spamrats.com'),
                       Provider('dyna.spamrats.com'),
                       Provider('auth.spamrats.com'),Provider('noptr.spamrats.com')]