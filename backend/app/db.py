"""Conexion a SQLite y dependencia de FastAPI.

sqlite3 de la libreria estandar, sin ORM: el requisito critico es controlar la
transaccion exacta (BEGIN IMMEDIATE, UPDATE condicional, rowcount) y un ORM
mete manejo de sesiones y threading encima sin aportar nada aqui.
"""

import sqlite3
from collections.abc import Iterator
from pathlib import Path

from .config import RUTA_BD


def conectar(ruta: Path | str | None = None) -> sqlite3.Connection:
    conexion = sqlite3.connect(
        str(ruta or RUTA_BD),
        # FastAPI atiende los endpoints sincronos en su threadpool, asi que la
        # conexion se crea en un hilo y se usa en ese mismo hilo, pero sqlite3
        # no puede comprobarlo por si solo.
        check_same_thread=False,
        # Las transacciones se abren a mano con BEGIN IMMEDIATE. Sin esto,
        # sqlite3 abriria una implicita y perderiamos el candado de escritura.
        isolation_level=None,
    )
    conexion.row_factory = sqlite3.Row
    # WAL: lectores y escritor no se bloquean entre si.
    conexion.execute("PRAGMA journal_mode=WAL")
    conexion.execute("PRAGMA foreign_keys=ON")
    # Ante un candado ocupado, espera en vez de fallar: es lo que hace que 50
    # compras concurrentes se serialicen en lugar de reventar con SQLITE_BUSY.
    conexion.execute("PRAGMA busy_timeout=5000")
    return conexion


def obtener_bd() -> Iterator[sqlite3.Connection]:
    """Una conexion por request, cerrada siempre al terminar."""
    conexion = conectar()
    try:
        yield conexion
    finally:
        conexion.close()
