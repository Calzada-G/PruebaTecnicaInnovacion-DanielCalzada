"""Reglas de negocio del recomendador, empezando por las bloqueantes."""

import pytest

from app.services import compra_service, recomendacion_service
from scripts.construir_relaciones import relaciones_por_atributos
from app.recomendador.historico import calcular_reglas
from app.repositories import relaciones_repo

TODAS_LAS_TIENDAS = ["cdmx", "cancun", "merida", "chihuahua", "monterrey"]


@pytest.fixture()
def bd_con_relaciones(bd):
    """Base sembrada y con las relaciones ya materializadas."""
    combinadas = {}
    for relacion in relaciones_por_atributos(bd) + calcular_reglas(bd):
        combinadas[
            (relacion["sku_origen"], relacion["sku_destino"], relacion["tipo"])
        ] = relacion
    bd.execute("BEGIN IMMEDIATE")
    relaciones_repo.reemplazar(bd, list(combinadas.values()))
    bd.commit()
    return bd


def skus_recomendados(resultado: dict) -> set[str]:
    skus = {c["sku"] for c in resultado["complementos"]}
    if resultado["sustituto"]:
        skus.add(resultado["sustituto"]["sku"])
    return skus


def test_nunca_recomienda_un_producto_sin_existencia(bd_con_relaciones):
    """Requisito bloqueante: solo se recomienda lo que se puede vender."""
    bd = bd_con_relaciones
    bd.execute("UPDATE productos SET stock = 0 WHERE sku IN ('SKU004','SKU007','SKU012')")
    bd.execute("UPDATE productos SET activo = 0 WHERE sku IN ('SKU026','SKU011')")
    bd.commit()
    prohibidos = {"SKU004", "SKU007", "SKU012", "SKU026", "SKU011"}

    for sku in [f["sku"] for f in bd.execute("SELECT sku FROM productos")]:
        for tienda in TODAS_LAS_TIENDAS:
            recomendados = skus_recomendados(
                recomendacion_service.recomendar(bd, sku, tienda)
            )
            assert not (recomendados & prohibidos), (
                f"{sku}@{tienda} recomendo {recomendados & prohibidos}"
            )


def test_agotar_un_sku_comprandolo_lo_saca_de_las_recomendaciones(bd_con_relaciones):
    bd = bd_con_relaciones
    antes = skus_recomendados(recomendacion_service.recomendar(bd, "SKU001", "monterrey"))
    assert "SKU004" in antes

    stock = bd.execute("SELECT stock FROM productos WHERE sku='SKU004'").fetchone()[
        "stock"
    ]
    compra_service.comprar(bd, "monterrey", [{"sku": "SKU004", "cantidad": stock}])

    despues = skus_recomendados(recomendacion_service.recomendar(bd, "SKU001", "monterrey"))
    assert "SKU004" not in despues


def test_no_recomienda_lo_que_ya_esta_en_el_ticket(bd_con_relaciones):
    sin_excluir = skus_recomendados(
        recomendacion_service.recomendar(bd_con_relaciones, "SKU001", "monterrey")
    )
    excluidos = {"SKU004", "SKU002"}
    assert excluidos <= sin_excluir

    resultado = recomendacion_service.recomendar(
        bd_con_relaciones, "SKU001", "monterrey", excluir=excluidos
    )
    assert not (skus_recomendados(resultado) & excluidos)


def test_merida_recomienda_pese_a_no_tener_una_sola_venta(bd_con_relaciones):
    """Arranque en frio de tienda: Merida no aparece en sales.csv."""
    ventas = bd_con_relaciones.execute(
        "SELECT COUNT(*) c FROM ventas WHERE tienda_id = 'merida'"
    ).fetchone()["c"]
    assert ventas == 0

    for sku in ("SKU005", "SKU010", "SKU024"):
        resultado = recomendacion_service.recomendar(bd_con_relaciones, sku, "merida")
        assert skus_recomendados(resultado), f"{sku} no devolvio nada en Merida"


def test_en_plaza_costera_propone_el_material_que_aguanta_el_salitre(
    bd_con_relaciones,
):
    for sku_carbono, sku_inoxidable in (("SKU005", "SKU007"), ("SKU024", "SKU025")):
        for tienda in ("merida", "cancun"):
            resultado = recomendacion_service.recomendar(
                bd_con_relaciones, sku_carbono, tienda
            )
            assert resultado["sustituto"] is not None
            assert resultado["sustituto"]["sku"] == sku_inoxidable


def test_no_propone_sustituto_si_el_ancla_ya_es_el_adecuado(bd_con_relaciones):
    assert (
        recomendacion_service.recomendar(bd_con_relaciones, "SKU007", "merida")[
            "sustituto"
        ]
        is None
    )
    assert (
        recomendacion_service.recomendar(bd_con_relaciones, "SKU005", "cdmx")[
            "sustituto"
        ]
        is None
    )


def test_el_regulador_sin_ventas_se_recomienda_con_el_soplete(bd_con_relaciones):
    """Arranque en frio de producto: SKU027 no aparece en ningun ticket."""
    ventas = bd_con_relaciones.execute(
        "SELECT COUNT(*) c FROM ventas WHERE sku = 'SKU027'"
    ).fetchone()["c"]
    assert ventas == 0

    for tienda in TODAS_LAS_TIENDAS:
        recomendados = skus_recomendados(
            recomendacion_service.recomendar(bd_con_relaciones, "SKU001", tienda)
        )
        assert "SKU027" in recomendados


def test_nunca_ofrece_como_complemento_algo_de_la_misma_familia(bd_con_relaciones):
    """SKU005 y SKU006 co-ocurren en T036, pero son alternativas entre si.

    Si el historico colara ese par como complemento, en Merida el sistema
    diria a la vez 'cambialo por el inoxidable' y 'llevate el galvanizado'.
    """
    for ancla, tienda in (("SKU005", "merida"), ("SKU005", "cdmx"), ("SKU010", "cancun")):
        resultado = recomendacion_service.recomendar(bd_con_relaciones, ancla, tienda)
        complementos = {c["sku"] for c in resultado["complementos"]}
        familia = {
            "SKU005": {"SKU006", "SKU007"},
            "SKU010": {"SKU011"},
        }[ancla]
        assert not (complementos & familia), f"{ancla}@{tienda}: {complementos & familia}"


def test_bloquear_una_relacion_la_saca_del_mostrador(bd_con_relaciones):
    bd = bd_con_relaciones
    assert "SKU004" in skus_recomendados(
        recomendacion_service.recomendar(bd, "SKU001", "monterrey")
    )

    fila = bd.execute(
        """SELECT id FROM relaciones
            WHERE sku_origen='SKU001' AND sku_destino='SKU004' AND tipo='complemento'"""
    ).fetchone()
    relaciones_repo.actualizar(bd, fila["id"], {"estado": "bloqueada"})
    bd.commit()

    assert "SKU004" not in skus_recomendados(
        recomendacion_service.recomendar(bd, "SKU001", "monterrey")
    )


def test_fijar_una_relacion_la_pone_primero(bd_con_relaciones):
    bd = bd_con_relaciones
    fila = bd.execute(
        """SELECT id FROM relaciones
            WHERE sku_origen='SKU001' AND sku_destino='SKU020' AND tipo='complemento'"""
    ).fetchone()
    relaciones_repo.actualizar(bd, fila["id"], {"estado": "fijada"})
    bd.commit()

    complementos = recomendacion_service.recomendar(bd, "SKU001", "monterrey")[
        "complementos"
    ]
    assert complementos[0]["sku"] == "SKU020"


def test_el_peso_manual_manda_sobre_el_score_calculado(bd_con_relaciones):
    bd = bd_con_relaciones
    fila = bd.execute(
        """SELECT id FROM relaciones
            WHERE sku_origen='SKU001' AND sku_destino='SKU020' AND tipo='complemento'"""
    ).fetchone()
    relaciones_repo.actualizar(bd, fila["id"], {"peso_manual": 0.01})
    bd.commit()

    complementos = recomendacion_service.recomendar(bd, "SKU001", "monterrey")[
        "complementos"
    ]
    posicion = [c["sku"] for c in complementos]
    assert posicion[-1] == "SKU020" or "SKU020" not in posicion


def test_cuando_el_historico_corrobora_se_muestran_los_tickets(bd_con_relaciones):
    """SKU001->SKU004 lo proponen las dos fuentes; debe citarse la evidencia."""
    complementos = recomendacion_service.recomendar(
        bd_con_relaciones, "SKU001", "monterrey"
    )["complementos"]
    cartucho = next(c for c in complementos if c["sku"] == "SKU004")

    assert cartucho["soporte"] == 2
    assert cartucho["lift"] > 1


def test_la_api_valida_producto_y_tienda(cliente):
    assert cliente.get("/api/recomendaciones?sku=NOPE&tienda=cdmx").status_code == 404
    assert (
        cliente.get("/api/recomendaciones?sku=SKU001&tienda=narnia").status_code == 404
    )
