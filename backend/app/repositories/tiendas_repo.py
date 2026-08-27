"""SQL de tiendas.

Existe porque el perfil de plaza dejo de leerse en un solo sitio: lo consultan
el recomendador, el diagnostico y el listado. Tenerlo repartido en tres SELECT
sueltos era la via rapida para que un dia dejaran de coincidir.
"""

import sqlite3

CAMPOS = "id, nombre, perfil, acento"


def listar(bd: sqlite3.Connection) -> list[sqlite3.Row]:
    return bd.execute(f"SELECT {CAMPOS} FROM tiendas ORDER BY nombre").fetchall()


def obtener(bd: sqlite3.Connection, tienda_id: str) -> sqlite3.Row | None:
    return bd.execute(
        f"SELECT {CAMPOS} FROM tiendas WHERE id = ?", (tienda_id,)
    ).fetchone()


def perfiles(bd: sqlite3.Connection) -> dict[str, str]:
    """Perfil por tienda, tal como lo consume el recomendador por atributos."""
    return {f["id"]: f["perfil"] for f in listar(bd)}


def contar(bd: sqlite3.Connection) -> int:
    return bd.execute("SELECT COUNT(*) AS n FROM tiendas").fetchone()["n"]
