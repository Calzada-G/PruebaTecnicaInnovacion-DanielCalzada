"""Todo el SQL de productos e inventario. Los servicios no conocen SQLite."""

import sqlite3

CAMPOS = (
    "sku, nombre, descripcion, categoria, material, uso_recomendado, "
    "precio, stock, activo"
)


def listar(
    bd: sqlite3.Connection,
    q: str | None = None,
    tienda: str | None = None,
    solo_activos: bool = True,
) -> list[sqlite3.Row]:
    """Busca por texto y, con tienda, prioriza lo que mas se mueve ahi.

    El inventario es compartido, asi que la tienda no cambia el stock: cambia el
    orden. El vendedor encuentra antes lo que su plaza vende, que es justo lo
    que hace util el selector de tienda tambien en el catalogo.
    """
    condiciones = []
    parametros: list[object] = []

    if solo_activos:
        condiciones.append("p.activo = 1")
    if q:
        condiciones.append(
            "(p.nombre LIKE ? OR p.sku LIKE ? OR p.categoria LIKE ?"
            " OR p.material LIKE ? OR p.uso_recomendado LIKE ?)"
        )
        patron = f"%{q}%"
        parametros.extend([patron] * 5)

    where = f"WHERE {' AND '.join(condiciones)}" if condiciones else ""

    if tienda:
        sql = f"""
            SELECT {CAMPOS} FROM productos p
            {where}
            ORDER BY (
                SELECT COALESCE(SUM(v.cantidad), 0) FROM ventas v
                 WHERE v.sku = p.sku AND v.tienda_id = ?
            ) DESC, p.nombre
        """
        parametros.append(tienda)
    else:
        sql = f"SELECT {CAMPOS} FROM productos p {where} ORDER BY p.nombre"

    return bd.execute(sql, parametros).fetchall()


def obtener(bd: sqlite3.Connection, sku: str) -> sqlite3.Row | None:
    return bd.execute(
        f"SELECT {CAMPOS} FROM productos WHERE sku = ?", (sku,)
    ).fetchone()


def insertar(bd: sqlite3.Connection, datos: dict) -> None:
    bd.execute(
        """INSERT INTO productos
           (sku, nombre, descripcion, categoria, material, uso_recomendado,
            precio, stock)
           VALUES (:sku, :nombre, :descripcion, :categoria, :material,
                   :uso_recomendado, :precio, :stock)""",
        datos,
    )


def actualizar(bd: sqlite3.Connection, sku: str, cambios: dict) -> int:
    """Aplica solo los campos recibidos. Devuelve filas afectadas."""
    asignaciones = ", ".join(f"{campo} = :{campo}" for campo in cambios)
    cur = bd.execute(
        f"""UPDATE productos
               SET {asignaciones}, actualizado_en = datetime('now')
             WHERE sku = :sku""",
        {**cambios, "sku": sku},
    )
    return cur.rowcount


def desactivar(bd: sqlite3.Connection, sku: str) -> int:
    """Borrado logico. Nunca DELETE: ventas y movimientos referencian el SKU."""
    cur = bd.execute(
        """UPDATE productos
              SET activo = 0, actualizado_en = datetime('now')
            WHERE sku = ? AND activo = 1""",
        (sku,),
    )
    return cur.rowcount


def descontar_stock(bd: sqlite3.Connection, sku: str, cantidad: int) -> int:
    """El corazon del requisito de no sobreventa.

    La validacion vive en el WHERE, no en Python: entre un SELECT y un UPDATE
    cabe otra transaccion. Devuelve rowcount; 0 significa que no se pudo vender
    (sin stock, inexistente o inactivo) y obliga a abortar el ticket entero.
    """
    cur = bd.execute(
        """UPDATE productos
              SET stock = stock - ?, actualizado_en = datetime('now')
            WHERE sku = ? AND activo = 1 AND stock >= ?""",
        (cantidad, sku, cantidad),
    )
    return cur.rowcount


def stock_actual(bd: sqlite3.Connection, sku: str) -> int | None:
    fila = bd.execute("SELECT stock FROM productos WHERE sku = ?", (sku,)).fetchone()
    return None if fila is None else fila["stock"]


def registrar_movimiento(
    bd: sqlite3.Connection,
    sku: str,
    delta: int,
    stock_final: int,
    motivo: str,
    tienda_id: str | None = None,
    ticket_id: str | None = None,
) -> None:
    bd.execute(
        """INSERT INTO movimientos_inventario
           (sku, delta, stock_final, motivo, tienda_id, ticket_id)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (sku, delta, stock_final, motivo, tienda_id, ticket_id),
    )
