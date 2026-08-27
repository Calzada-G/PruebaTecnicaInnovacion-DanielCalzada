"""El requisito bloqueante numero uno: el inventario nunca queda negativo.

Los hilos llaman a compra_service con su propia conexion, sin pasar por HTTP.
Asi se mide la transaccion de SQLite, que es donde vive la garantia, y no el
threadpool de FastAPI ni el cliente de pruebas.
"""

import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from app.db import conectar
from app.errores import StockInsuficiente
from app.services import compra_service

TIENDAS = ["cdmx", "cancun", "merida", "chihuahua", "monterrey"]


def _comprar_una(ruta: Path, sku: str, tienda: str) -> str:
    conexion = conectar(ruta)
    try:
        compra_service.comprar(conexion, tienda, [{"sku": sku, "cantidad": 1}])
        return "ok"
    except StockInsuficiente:
        return "sin_stock"
    except sqlite3.OperationalError as exc:
        # No se captura para tolerarlo: se distingue para que, si apareciera,
        # el fallo diga "candado" y no se confunda con una sobreventa.
        return f"candado: {exc}"
    finally:
        conexion.close()


def test_50_hilos_contra_stock_8_venden_exactamente_8(bd, ruta_bd: Path):
    sku = "SKU027"
    bd.execute("UPDATE productos SET stock = 8 WHERE sku = ?", (sku,))
    bd.commit()

    with ThreadPoolExecutor(max_workers=50) as pool:
        resultados = list(
            pool.map(
                lambda i: _comprar_una(ruta_bd, sku, TIENDAS[i % len(TIENDAS)]),
                range(50),
            )
        )

    exitos = resultados.count("ok")
    candados = [r for r in resultados if r.startswith("candado")]
    stock_final = bd.execute(
        "SELECT stock FROM productos WHERE sku = ?", (sku,)
    ).fetchone()["stock"]

    assert not candados, f"SQLite devolvio candado ocupado: {candados[:3]}"
    assert exitos == 8, f"Se vendieron {exitos} unidades de 8 disponibles."
    assert stock_final == 0
    assert len(resultados) == 50


def test_el_libro_de_movimientos_cuadra_con_el_stock(bd, ruta_bd: Path):
    """Si los deltas no suman el stock final, hubo una escritura fuera de control."""
    sku = "SKU027"
    inicial = bd.execute(
        "SELECT stock FROM productos WHERE sku = ?", (sku,)
    ).fetchone()["stock"]

    with ThreadPoolExecutor(max_workers=20) as pool:
        list(pool.map(lambda i: _comprar_una(ruta_bd, sku, "cdmx"), range(20)))

    fila = bd.execute(
        """SELECT p.stock, COALESCE(SUM(m.delta), 0) AS suma
             FROM productos p
             LEFT JOIN movimientos_inventario m
                    ON m.sku = p.sku AND m.motivo = 'venta'
            WHERE p.sku = ?""",
        (sku,),
    ).fetchone()

    assert fila["stock"] == inicial + fila["suma"]
    assert fila["stock"] >= 0


def test_ningun_producto_queda_con_stock_negativo(bd, ruta_bd: Path):
    skus = ["SKU027", "SKU003", "SKU026"]
    for sku in skus:
        bd.execute("UPDATE productos SET stock = 3 WHERE sku = ?", (sku,))
    bd.commit()

    with ThreadPoolExecutor(max_workers=30) as pool:
        list(
            pool.map(
                lambda i: _comprar_una(ruta_bd, skus[i % len(skus)], "monterrey"),
                range(30),
            )
        )

    negativos = bd.execute("SELECT sku FROM productos WHERE stock < 0").fetchall()
    assert not negativos
    for sku in skus:
        assert (
            bd.execute(
                "SELECT stock FROM productos WHERE sku = ?", (sku,)
            ).fetchone()["stock"]
            == 0
        )
