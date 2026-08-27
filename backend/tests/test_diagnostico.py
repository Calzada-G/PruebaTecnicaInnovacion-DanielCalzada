"""El sistema detecta sus propias carencias sin que nadie se las capture.

Lo que se prueba aqui no es que el texto sea bonito, sino que los hallazgos
salgan de los datos: si manana Merida vende, el aviso de plaza sin historial
tiene que desaparecer solo.
"""

from app.services import diagnostico_service


def claves(diagnostico: dict) -> set[str]:
    return {h["clave"] for h in diagnostico["hallazgos"]}


def hallazgo(diagnostico: dict, clave: str) -> dict | None:
    return next((h for h in diagnostico["hallazgos"] if h["clave"] == clave), None)


def test_merida_se_reporta_sin_historial_y_las_demas_no(bd):
    merida = diagnostico_service.diagnosticar(bd, "merida")
    cdmx = diagnostico_service.diagnosticar(bd, "cdmx")

    assert merida["tickets_en_la_plaza"] == 0
    assert "plaza_sin_historial" in claves(merida)
    assert cdmx["tickets_en_la_plaza"] > 0
    assert "plaza_sin_historial" not in claves(cdmx)


def test_el_aviso_de_plaza_sin_historial_desaparece_al_vender_ahi(bd):
    """No es una excepcion escrita a mano para Merida: se recalcula cada vez."""
    from app.services import compra_service

    compra_service.comprar(bd, "merida", [{"sku": "SKU001", "cantidad": 1}])

    assert "plaza_sin_historial" not in claves(
        diagnostico_service.diagnosticar(bd, "merida")
    )


def test_detecta_el_producto_que_nunca_se_vendio(bd):
    """SKU027 es el unico SKU sin una sola linea en sales.csv."""
    detectado = hallazgo(diagnostico_service.diagnosticar(bd, "cancun"), "nunca_vendido")

    assert detectado is not None
    assert [p["sku"] for p in detectado["productos"]] == ["SKU027"]


def test_agotar_un_producto_lo_convierte_en_hallazgo(bd):
    from app.services import compra_service

    antes = claves(diagnostico_service.diagnosticar(bd, "cdmx"))
    stock = bd.execute("SELECT stock FROM productos WHERE sku = 'SKU001'").fetchone()[0]
    compra_service.comprar(bd, "cdmx", [{"sku": "SKU001", "cantidad": stock}])

    despues = hallazgo(diagnostico_service.diagnosticar(bd, "cdmx"), "sin_existencia")

    assert "sin_existencia" not in antes
    assert despues is not None
    assert "SKU001" in [p["sku"] for p in despues["productos"]]


def test_solo_se_propone_como_paquete_una_pareja_vendible(con_relaciones):
    """Recomendar un paquete con una pieza agotada seria vender humo."""
    bd = con_relaciones
    propuesta = hallazgo(
        diagnostico_service.diagnosticar(bd, "monterrey"), "promocion_con_respaldo"
    )

    assert propuesta is not None
    for citado in propuesta["productos"]:
        fila = bd.execute(
            "SELECT stock, activo FROM productos WHERE sku = ?", (citado["sku"],)
        ).fetchone()
        assert fila["stock"] > 0 and fila["activo"]


def test_cada_hallazgo_trae_titulo_detalle_y_accion(cliente):
    """Un diagnostico sin que-hacer solo genera ansiedad."""
    cuerpo = cliente.get("/api/diagnostico?tienda=merida").json()

    assert cuerpo["hallazgos"]
    for encontrado in cuerpo["hallazgos"]:
        assert encontrado["nivel"] in ("alerta", "aviso", "oportunidad")
        assert encontrado["titulo"] and encontrado["detalle"] and encontrado["accion"]
        # Se citan como mucho MAXIMO_CITADOS aunque el total sea mayor.
        assert len(encontrado["productos"]) <= encontrado["total"] or not (
            encontrado["total"]
        )
