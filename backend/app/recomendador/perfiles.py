"""Perfil de plaza: que tan adecuado es un producto para una tienda.

Esta es la capa que resuelve el arranque en frio de tienda. Merida no aparece
en sales.csv, asi que ninguna regla de asociacion puede hablar de ella; su
perfil si, porque no depende del historico sino de los atributos del producto.
"""

import unicodedata

AMBIENTES = ("interior", "humedad", "costero", "sol", "neutro")


def normalizar(texto: str) -> str:
    """Minusculas y sin acentos: los CSV traen 'perforación', 'eléctrico'."""
    descompuesto = unicodedata.normalize("NFKD", texto.lower())
    return "".join(c for c in descompuesto if not unicodedata.combining(c))


def ambiente(uso_recomendado: str, material: str) -> str:
    """Clasifica el ambiente para el que fue hecho un producto.

    Se lee de uso_recomendado y material, no de una tabla de SKUs: asi un
    producto dado de alta hoy queda clasificado sin tocar codigo.
    """
    texto = normalizar(f"{uso_recomendado} {material}")

    # 'protegido de la luz solar' es lo contrario de resistir el sol, y contiene
    # la palabra 'solar'. Va primero o el tubo de PVC acabaria clasificado como
    # apto para intemperie, que es justo el error que este sistema debe evitar.
    if "protegido" in texto:
        return "interior"
    if any(p in texto for p in ("costero", "salin", "marino", "316")):
        return "costero"
    if "solar" in texto or "uv" in texto.split():
        return "sol"
    if any(p in texto for p in ("humedad", "galvaniz", "intemperie", "uso rudo")):
        return "humedad"
    if "interior" in texto:
        return "interior"
    if "exterior" in texto:
        return "humedad"
    return "neutro"


# Cuanto le sirve a cada plaza un producto de cada ambiente, de 0 a 1.
#
# CONOCIMIENTO DE NEGOCIO DECLARADO, no derivado de los datos. Los cuatro
# perfiles con historico (CDMX, Cancun, Chihuahua, Monterrey) son coherentes
# con lo que esas tiendas venden; el de Merida esta asignado por su clima y no
# tiene respaldo en sales.csv. Un ajuste de estos numeros cambia que sustituto
# propone el sistema, y por eso viven aqui y no repartidos por el codigo.
ADECUACION: dict[str, dict[str, float]] = {
    "interior_urbano": {
        "interior": 1.00, "humedad": 0.55, "costero": 0.30, "sol": 0.35, "neutro": 0.70
    },
    "costero_salino": {
        "interior": 0.20, "humedad": 0.60, "costero": 1.00, "sol": 0.55, "neutro": 0.70
    },
    "sol_directo_seco": {
        "interior": 0.45, "humedad": 0.40, "costero": 0.35, "sol": 1.00, "neutro": 0.70
    },
    "taller_metalmecanico": {
        "interior": 0.90, "humedad": 0.60, "costero": 0.35, "sol": 0.40, "neutro": 0.70
    },
}

# La justificacion se arma comparando: que ambiente cubre el producto actual y
# como es la plaza. Una frase fija por perfil se contradecia con la ventaja real
# del sustituto (proponia CPVC anti-UV "porque el aire salino corroe"), y una
# justificacion que no se sostiene es peor que ninguna: el vendedor la repite
# al cliente y queda mal.
AMBIENTE_TEXTO = {
    "interior": "interior",
    "humedad": "exterior con humedad",
    "costero": "ambiente costero salino",
    "sol": "exposicion solar directa",
    "neutro": "uso general",
}

PLAZA_TEXTO = {
    "costero_salino": "costera y salina",
    "sol_directo_seco": "de sol directo y clima seco",
    "interior_urbano": "de trabajo en interior",
    "taller_metalmecanico": "de taller bajo techo",
}

VENTAJA_AMBIENTE = {
    "costero": "resiste corrosion salina",
    "sol": "resiste radiacion solar directa",
    "humedad": "resiste humedad",
    "interior": "suficiente para interior y mas barato",
    "neutro": "sirve igual en cualquier plaza",
}


def adecuacion(perfil: str, ambiente_producto: str) -> float:
    return ADECUACION.get(perfil, ADECUACION["interior_urbano"]).get(
        ambiente_producto, 0.5
    )
