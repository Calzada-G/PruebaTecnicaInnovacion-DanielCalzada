"""Compra por tienda contra el inventario compartido.

Requisito bloqueante: el inventario nunca queda negativo, ni con compras
concurrentes desde tiendas distintas. Todo el ticket es atomico: si una linea
no alcanza, no se descuenta ninguna.
"""

import json
import sqlite3
from datetime import date

from ..errores import (
    CompraInvalida,
    ProductoNoEncontrado,
    StockInsuficiente,
    TiendaNoEncontrada,
)
from ..repositories import productos_repo, tiendas_repo, ventas_repo


def _agrupar(items: list[dict]) -> dict[str, int]:
    """Suma las lineas repetidas del mismo SKU, como haria cualquier mostrador."""
    agrupado: dict[str, int] = {}
    for item in items:
        agrupado[item["sku"]] = agrupado.get(item["sku"], 0) + item["cantidad"]
    return agrupado


def comprar(
    bd: sqlite3.Connection,
    tienda: str,
    items: list[dict],
    clave_idempotencia: str | None = None,
) -> dict:
    if not items:
        raise CompraInvalida("El ticket no tiene lineas.")

    cantidades = _agrupar(items)
    fecha = date.today().isoformat()

    cur = bd.cursor()
    # IMMEDIATE toma el candado de escritura al abrir, no en el primer UPDATE:
    # sin esto dos tickets podrian leer el mismo stock antes de escribir.
    cur.execute("BEGIN IMMEDIATE")
    try:
        if tiendas_repo.obtener(bd, tienda) is None:
            raise TiendaNoEncontrada(tienda)

        if clave_idempotencia and not ventas_repo.reservar_clave(
            bd, clave_idempotencia
        ):
            # Otra peticion con la misma clave ya paso por aqui. No se descuenta
            # nada y se devuelve su respuesta original.
            bd.rollback()
            guardada = ventas_repo.leer_respuesta(bd, clave_idempotencia)
            if guardada:
                return {**json.loads(guardada), "repetida": True}
            raise CompraInvalida(
                "Hay una compra en curso con esa Idempotency-Key. Reintenta."
            )

        ticket_id = ventas_repo.siguiente_ticket(bd)
        lineas = []
        total = 0.0

        for sku, cantidad in cantidades.items():
            if productos_repo.descontar_stock(bd, sku, cantidad) != 1:
                # El UPDATE no afecto ninguna fila. Desde SQL los tres motivos
                # son indistinguibles, asi que se consultan DESPUES solo para
                # decir la verdad en el mensaje: la decision de vender ya la
                # tomo el WHERE, nunca Python.
                fallido = productos_repo.obtener(bd, sku)
                if fallido is None:
                    raise ProductoNoEncontrado(sku)
                if not fallido["activo"]:
                    raise CompraInvalida(
                        f"{sku} esta dado de baja y no se puede vender."
                    )
                raise StockInsuficiente(sku, cantidad, fallido["stock"])

            producto = productos_repo.obtener(bd, sku)
            subtotal = round(producto["precio"] * cantidad, 2)
            total += subtotal

            ventas_repo.insertar_linea(bd, ticket_id, sku, cantidad, tienda, fecha)
            productos_repo.registrar_movimiento(
                bd, sku, -cantidad, producto["stock"], "venta", tienda, ticket_id
            )
            lineas.append(
                {
                    "sku": sku,
                    "nombre": producto["nombre"],
                    "cantidad": cantidad,
                    "precio_unitario": producto["precio"],
                    "subtotal": subtotal,
                    "stock_restante": producto["stock"],
                }
            )

        respuesta = {
            "ticket_id": ticket_id,
            "tienda": tienda,
            "fecha": fecha,
            "lineas": lineas,
            "total": round(total, 2),
            "repetida": False,
        }

        if clave_idempotencia:
            ventas_repo.guardar_respuesta(
                bd, clave_idempotencia, json.dumps(respuesta)
            )

        bd.commit()
        return respuesta
    except Exception:
        bd.rollback()
        raise
