"""Ajustes del negocio sobre las relaciones y pesos de las fuentes.

Existe por coherencia con el resto del backend: el limite transaccional vive en
services/, nunca en un router. Antes estas dos operaciones abrian la transaccion
dentro del propio router, que era la unica excepcion a la regla en todo el
proyecto y no se sostenia.
"""

import sqlite3

from ..errores import RelacionNoEncontrada
from ..repositories import relaciones_repo


def listar(
    bd: sqlite3.Connection, tipo: str | None = None, fuente: str | None = None
) -> list[dict]:
    return [dict(f) for f in relaciones_repo.listar(bd, tipo=tipo, fuente=fuente)]


def ajustar(bd: sqlite3.Connection, id_relacion: int, cambios: dict) -> dict:
    cur = bd.cursor()
    cur.execute("BEGIN IMMEDIATE")
    try:
        if relaciones_repo.obtener(bd, id_relacion) is None:
            raise RelacionNoEncontrada(id_relacion)
        if cambios:
            relaciones_repo.actualizar(bd, id_relacion, cambios)
        bd.commit()
    except Exception:
        bd.rollback()
        raise
    return dict(relaciones_repo.obtener(bd, id_relacion))


def leer_pesos(bd: sqlite3.Connection) -> dict[str, float]:
    return relaciones_repo.pesos(bd)


def guardar_pesos(bd: sqlite3.Connection, nuevos: dict[str, float]) -> dict[str, float]:
    cur = bd.cursor()
    cur.execute("BEGIN IMMEDIATE")
    try:
        relaciones_repo.guardar_pesos(bd, nuevos)
        bd.commit()
    except Exception:
        bd.rollback()
        raise
    return relaciones_repo.pesos(bd)
