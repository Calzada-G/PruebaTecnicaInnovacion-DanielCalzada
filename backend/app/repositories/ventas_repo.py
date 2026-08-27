"""SQL de ventas, tickets y control de idempotencia."""

import sqlite3


def existe_tienda(bd: sqlite3.Connection, tienda_id: str) -> bool:
    return (
        bd.execute("SELECT 1 FROM tiendas WHERE id = ?", (tienda_id,)).fetchone()
        is not None
    )


def siguiente_ticket(bd: sqlite3.Connection) -> str:
    """Continua la serie T001..T042 del historico.

    Solo se llama dentro de una transaccion BEGIN IMMEDIATE, que serializa a los
    escritores: por eso leer el maximo y sumar uno no puede dar un id repetido.
    """
    fila = bd.execute(
        "SELECT MAX(CAST(SUBSTR(ticket_id, 2) AS INTEGER)) AS n FROM ventas"
    ).fetchone()
    return f"T{(fila['n'] or 0) + 1:03d}"


def insertar_linea(
    bd: sqlite3.Connection,
    ticket_id: str,
    sku: str,
    cantidad: int,
    tienda_id: str,
    fecha: str,
) -> None:
    bd.execute(
        """INSERT INTO ventas (ticket_id, sku, cantidad, tienda_id, fecha)
           VALUES (?, ?, ?, ?, ?)""",
        (ticket_id, sku, cantidad, tienda_id, fecha),
    )


def reservar_clave(bd: sqlite3.Connection, clave: str) -> bool:
    """Intenta apropiarse de una Idempotency-Key.

    Devuelve False si otra peticion ya la tomo. La PK de `operaciones` es el
    candado: no hay ventana entre comprobar y reservar porque es el mismo INSERT.
    """
    try:
        bd.execute("INSERT INTO operaciones (clave) VALUES (?)", (clave,))
        return True
    except sqlite3.IntegrityError:
        return False


def guardar_respuesta(bd: sqlite3.Connection, clave: str, respuesta: str) -> None:
    bd.execute(
        "UPDATE operaciones SET respuesta = ? WHERE clave = ?", (respuesta, clave)
    )


def leer_respuesta(bd: sqlite3.Connection, clave: str) -> str | None:
    fila = bd.execute(
        "SELECT respuesta FROM operaciones WHERE clave = ?", (clave,)
    ).fetchone()
    return None if fila is None else fila["respuesta"]




