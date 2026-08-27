"""En que estado esta la API: version, base y contenido.

Lo consumen tres sitios -el banner de arranque, la portada y /api/salud- y por
eso vive aqui y no en cada uno. Si el banner dijera 28 productos y la portada
otra cosa, el dato dejaria de servir para diagnosticar nada.
"""

import sqlite3

from .. import db as modulo_db
from ..config import ORIGENES_CORS, VERSION
from ..repositories import productos_repo, relaciones_repo, tiendas_repo, ventas_repo


def contenido(bd: sqlite3.Connection) -> dict:
    return {
        "tiendas": tiendas_repo.contar(bd),
        "productos_activos": productos_repo.contar_activos(bd),
        "tickets": ventas_repo.contar_tickets(bd),
        "relaciones": relaciones_repo.contar(bd),
        "relaciones_redactadas_por_ia": relaciones_repo.contar_redactadas_por_ia(bd),
    }


def estado(bd: sqlite3.Connection) -> dict:
    """Resumen tolerante a una base a medio montar.

    Si el archivo no existe, sqlite3 lo crea vacio y las consultas fallan por
    tabla inexistente. Ese es justamente el caso que hay que CONTAR -falta
    sembrar- y no un error que tumbe el arranque de la API.
    """
    datos = {
        "estado": "listo",
        "version": VERSION,
        # Se lee del modulo db y no de config porque los tests apuntan la
        # base a un temporal justo ahi.
        "base_de_datos": str(modulo_db.RUTA_BD),
        "origenes_cors": ORIGENES_CORS,
        "contenido": None,
    }
    try:
        datos["contenido"] = contenido(bd)
    except sqlite3.Error:
        return datos | {"estado": "sin base de datos"}

    if not datos["contenido"]["productos_activos"]:
        datos["estado"] = "base vacia"
    return datos
