"""SQL del analisis generado por el LLM."""

import sqlite3


def ultimo(bd: sqlite3.Connection, tienda_id: str) -> sqlite3.Row | None:
    """El analisis mas reciente de esa plaza, sea del estado que sea."""
    return bd.execute(
        """SELECT huella, modelo, contenido, creado_en
             FROM analisis_ia
            WHERE tienda_id = ?
            ORDER BY creado_en DESC, id DESC
            LIMIT 1""",
        (tienda_id,),
    ).fetchone()


def por_huella(
    bd: sqlite3.Connection, tienda_id: str, huella: str
) -> sqlite3.Row | None:
    """El analisis de ESTE estado exacto del sistema, si ya se pidio antes.

    Es la consulta que evita la llamada: si el sistema no ha cambiado, la
    respuesta ya esta escrita y no hay nada nuevo que preguntar.
    """
    return bd.execute(
        """SELECT huella, modelo, contenido, creado_en
             FROM analisis_ia
            WHERE tienda_id = ? AND huella = ?""",
        (tienda_id, huella),
    ).fetchone()


def guardar(
    bd: sqlite3.Connection,
    tienda_id: str,
    huella: str,
    modelo: str,
    contenido: str,
) -> None:
    bd.execute(
        """INSERT INTO analisis_ia (tienda_id, huella, modelo, contenido)
           VALUES (?, ?, ?, ?)
           ON CONFLICT (tienda_id, huella) DO UPDATE SET
               modelo    = excluded.modelo,
               contenido = excluded.contenido,
               creado_en = datetime('now')""",
        (tienda_id, huella, modelo, contenido),
    )
