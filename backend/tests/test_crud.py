"""CRUD de productos, con foco en el borrado logico y sus consecuencias."""

import pytest

from app.errores import ProductoDuplicado, ProductoNoEncontrado
from app.services import catalogo_service

NUEVO = {
    "sku": "SKU900",
    "nombre": "Brocha de 4 pulgadas",
    "descripcion": "Brocha de cerda natural",
    "categoria": "pintura",
    "material": "cerda natural",
    "uso_recomendado": "aplicacion de pintura en interior",
    "precio": 85.0,
    "stock": 12,
}


def test_el_alta_registra_el_stock_inicial_en_el_libro(bd):
    catalogo_service.crear(bd, dict(NUEVO))

    movimiento = bd.execute(
        "SELECT delta, stock_final, motivo FROM movimientos_inventario WHERE sku = ?",
        ("SKU900",),
    ).fetchone()

    assert movimiento["motivo"] == "alta"
    assert movimiento["delta"] == 12
    assert movimiento["stock_final"] == 12


def test_no_se_puede_dar_de_alta_un_sku_repetido(bd):
    catalogo_service.crear(bd, dict(NUEVO))
    with pytest.raises(ProductoDuplicado):
        catalogo_service.crear(bd, dict(NUEVO))


def test_el_patch_solo_toca_los_campos_enviados(bd):
    antes = catalogo_service.obtener(bd, "SKU001")

    despues = catalogo_service.actualizar(bd, "SKU001", {"precio": 499.0})

    assert despues["precio"] == 499.0
    assert despues["nombre"] == antes["nombre"]
    assert despues["stock"] == antes["stock"]
    assert despues["uso_recomendado"] == antes["uso_recomendado"]


def test_ajustar_el_stock_a_mano_queda_asentado(bd):
    catalogo_service.actualizar(bd, "SKU001", {"stock": 40})

    movimiento = bd.execute(
        """SELECT delta, stock_final, motivo FROM movimientos_inventario
            WHERE sku = 'SKU001' ORDER BY id DESC LIMIT 1"""
    ).fetchone()

    assert movimiento["motivo"] == "ajuste"
    assert movimiento["delta"] == 25
    assert movimiento["stock_final"] == 40


def test_la_baja_es_logica_y_conserva_el_historial(bd):
    ventas_antes = bd.execute(
        "SELECT COUNT(*) c FROM ventas WHERE sku = 'SKU001'"
    ).fetchone()["c"]

    catalogo_service.eliminar(bd, "SKU001")

    fila = bd.execute("SELECT activo FROM productos WHERE sku = 'SKU001'").fetchone()
    ventas_despues = bd.execute(
        "SELECT COUNT(*) c FROM ventas WHERE sku = 'SKU001'"
    ).fetchone()["c"]

    assert fila["activo"] == 0
    assert ventas_despues == ventas_antes


def test_un_producto_de_baja_desaparece_del_listado_operativo(bd):
    catalogo_service.eliminar(bd, "SKU001")

    activos = {p["sku"] for p in catalogo_service.listar(bd)}
    todos = {p["sku"] for p in catalogo_service.listar(bd, incluir_inactivos=True)}

    assert "SKU001" not in activos
    assert "SKU001" in todos


def test_operar_sobre_un_sku_inexistente_falla_igual_en_las_tres_rutas(bd):
    for operacion in (
        lambda: catalogo_service.obtener(bd, "NO-EXISTE"),
        lambda: catalogo_service.actualizar(bd, "NO-EXISTE", {"precio": 1.0}),
        lambda: catalogo_service.eliminar(bd, "NO-EXISTE"),
    ):
        with pytest.raises(ProductoNoEncontrado):
            operacion()


def test_la_busqueda_encuentra_por_uso_y_material_no_solo_por_nombre(bd):
    """El vendedor busca 'salino' o 'inoxidable', no el nombre exacto del SKU."""
    por_uso = {p["sku"] for p in catalogo_service.listar(bd, buscar="salino")}
    por_material = {p["sku"] for p in catalogo_service.listar(bd, buscar="inoxidable")}

    assert {"SKU007", "SKU025"} <= por_uso
    assert {"SKU007", "SKU025"} <= por_material


def test_la_api_rechaza_precio_y_stock_negativos(cliente):
    precio = cliente.post("/api/productos", json={**NUEVO, "precio": -1})
    stock = cliente.post("/api/productos", json={**NUEVO, "stock": -1})
    sin_nombre = cliente.post("/api/productos", json={**NUEVO, "nombre": ""})

    assert precio.status_code == 422
    assert stock.status_code == 422
    assert sin_nombre.status_code == 422
