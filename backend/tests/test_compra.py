"""Casos limite del flujo de compra."""

import pytest

from app.errores import CompraInvalida, ProductoNoEncontrado, StockInsuficiente
from app.services import compra_service


def stock(bd, sku: str) -> int:
    return bd.execute("SELECT stock FROM productos WHERE sku = ?", (sku,)).fetchone()[
        "stock"
    ]


def test_el_ticket_es_atomico_si_una_linea_no_alcanza(bd):
    antes = stock(bd, "SKU001")

    with pytest.raises(StockInsuficiente) as error:
        compra_service.comprar(
            bd,
            "cdmx",
            [{"sku": "SKU001", "cantidad": 1}, {"sku": "SKU027", "cantidad": 999}],
        )

    assert error.value.sku == "SKU027"
    assert error.value.disponible == 8
    # La linea que si alcanzaba tampoco se descuenta: o todo o nada.
    assert stock(bd, "SKU001") == antes
    assert bd.execute("SELECT COUNT(*) c FROM ventas WHERE ticket_id > 'T042'").fetchone()["c"] == 0


def test_la_misma_clave_de_idempotencia_no_descuenta_dos_veces(bd):
    antes = stock(bd, "SKU027")
    items = [{"sku": "SKU027", "cantidad": 2}]

    primera = compra_service.comprar(bd, "cdmx", items, clave_idempotencia="k-1")
    segunda = compra_service.comprar(bd, "cdmx", items, clave_idempotencia="k-1")

    assert primera["ticket_id"] == segunda["ticket_id"]
    assert primera["repetida"] is False
    assert segunda["repetida"] is True
    assert stock(bd, "SKU027") == antes - 2


def test_claves_de_idempotencia_distintas_si_descuentan_dos_veces(bd):
    antes = stock(bd, "SKU027")
    items = [{"sku": "SKU027", "cantidad": 2}]

    compra_service.comprar(bd, "cdmx", items, clave_idempotencia="k-1")
    compra_service.comprar(bd, "cdmx", items, clave_idempotencia="k-2")

    assert stock(bd, "SKU027") == antes - 4


def test_no_se_puede_vender_un_producto_dado_de_baja(bd):
    bd.execute("UPDATE productos SET activo = 0 WHERE sku = 'SKU013'")
    bd.commit()
    antes = stock(bd, "SKU013")

    with pytest.raises(CompraInvalida):
        compra_service.comprar(bd, "cdmx", [{"sku": "SKU013", "cantidad": 1}])

    assert stock(bd, "SKU013") == antes


def test_un_sku_inexistente_no_se_confunde_con_falta_de_stock(bd):
    with pytest.raises(ProductoNoEncontrado):
        compra_service.comprar(bd, "cdmx", [{"sku": "NO-EXISTE", "cantidad": 1}])


def test_las_lineas_repetidas_del_mismo_sku_se_suman(bd):
    antes = stock(bd, "SKU027")

    respuesta = compra_service.comprar(
        bd,
        "cdmx",
        [{"sku": "SKU027", "cantidad": 3}, {"sku": "SKU027", "cantidad": 2}],
    )

    assert len(respuesta["lineas"]) == 1
    assert respuesta["lineas"][0]["cantidad"] == 5
    assert stock(bd, "SKU027") == antes - 5


def test_sumadas_las_lineas_repetidas_tampoco_sobrevenden(bd):
    """Dos lineas de 5 contra stock 8 deben fallar, no colar 5 y luego 5."""
    with pytest.raises(StockInsuficiente):
        compra_service.comprar(
            bd,
            "cdmx",
            [{"sku": "SKU027", "cantidad": 5}, {"sku": "SKU027", "cantidad": 5}],
        )
    assert stock(bd, "SKU027") == 8


def test_la_compra_por_api_valida_cantidad_y_tienda(cliente):
    sin_lineas = cliente.post("/api/compras", json={"tienda": "cdmx", "items": []})
    cantidad_cero = cliente.post(
        "/api/compras",
        json={"tienda": "cdmx", "items": [{"sku": "SKU001", "cantidad": 0}]},
    )
    cantidad_negativa = cliente.post(
        "/api/compras",
        json={"tienda": "cdmx", "items": [{"sku": "SKU001", "cantidad": -3}]},
    )
    tienda_falsa = cliente.post(
        "/api/compras",
        json={"tienda": "narnia", "items": [{"sku": "SKU001", "cantidad": 1}]},
    )

    assert sin_lineas.status_code == 422
    assert cantidad_cero.status_code == 422
    assert cantidad_negativa.status_code == 422
    assert tienda_falsa.status_code == 404


def test_el_error_de_stock_dice_cuanto_queda(cliente):
    respuesta = cliente.post(
        "/api/compras",
        json={"tienda": "merida", "items": [{"sku": "SKU027", "cantidad": 50}]},
    )
    cuerpo = respuesta.json()

    assert respuesta.status_code == 409
    assert cuerpo["sku"] == "SKU027"
    assert cuerpo["disponible"] == 8
    assert "Quedan 8" in cuerpo["detail"]


def test_se_puede_comprar_desde_merida_pese_a_no_tener_historial(bd):
    """Merida no aparece en sales.csv, pero el inventario es compartido."""
    respuesta = compra_service.comprar(
        bd, "merida", [{"sku": "SKU007", "cantidad": 2}]
    )
    assert respuesta["tienda"] == "merida"
    assert stock(bd, "SKU007") == 78
