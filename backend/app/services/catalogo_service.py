"""Reglas de negocio del catalogo y limite transaccional de sus escrituras."""

import sqlite3

from ..errores import ProductoDuplicado, ProductoNoEncontrado
from ..repositories import productos_repo


def listar(
    bd: sqlite3.Connection,
    q: str | None = None,
    tienda: str | None = None,
    incluir_inactivos: bool = False,
) -> list[dict]:
    filas = productos_repo.listar(
        bd, q=q, tienda=tienda, solo_activos=not incluir_inactivos
    )
    return [dict(f) for f in filas]


def obtener(bd: sqlite3.Connection, sku: str) -> dict:
    fila = productos_repo.obtener(bd, sku)
    if fila is None:
        raise ProductoNoEncontrado(sku)
    return dict(fila)


def crear(bd: sqlite3.Connection, datos: dict) -> dict:
    cur = bd.cursor()
    cur.execute("BEGIN IMMEDIATE")
    try:
        if productos_repo.obtener(bd, datos["sku"]) is not None:
            raise ProductoDuplicado(datos["sku"])
        productos_repo.insertar(bd, datos)
        # El alta con existencias es la primera entrada del libro de inventario:
        # sin ella, el stock inicial no tendria de donde salir en la auditoria.
        if datos["stock"]:
            productos_repo.registrar_movimiento(
                bd, datos["sku"], datos["stock"], datos["stock"], "alta"
            )
        bd.commit()
    except Exception:
        bd.rollback()
        raise
    return obtener(bd, datos["sku"])


def actualizar(bd: sqlite3.Connection, sku: str, cambios: dict) -> dict:
    if not cambios:
        return obtener(bd, sku)

    cur = bd.cursor()
    cur.execute("BEGIN IMMEDIATE")
    try:
        anterior = productos_repo.obtener(bd, sku)
        if anterior is None:
            raise ProductoNoEncontrado(sku)

        if "activo" in cambios:
            cambios["activo"] = int(bool(cambios["activo"]))

        productos_repo.actualizar(bd, sku, cambios)

        # Un cambio de stock desde el catalogo es un ajuste manual de almacen y
        # queda en el mismo libro que las ventas, con su motivo propio.
        if "stock" in cambios and cambios["stock"] != anterior["stock"]:
            delta = cambios["stock"] - anterior["stock"]
            productos_repo.registrar_movimiento(
                bd, sku, delta, cambios["stock"], "ajuste"
            )
        bd.commit()
    except Exception:
        bd.rollback()
        raise
    return obtener(bd, sku)


def eliminar(bd: sqlite3.Connection, sku: str) -> None:
    """Borrado logico: el SKU sigue referenciado por ventas y movimientos."""
    cur = bd.cursor()
    cur.execute("BEGIN IMMEDIATE")
    try:
        if productos_repo.obtener(bd, sku) is None:
            raise ProductoNoEncontrado(sku)
        productos_repo.desactivar(bd, sku)
        bd.commit()
    except Exception:
        bd.rollback()
        raise
