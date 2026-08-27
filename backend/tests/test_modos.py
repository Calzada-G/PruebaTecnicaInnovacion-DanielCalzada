"""Los tres modos del panel tienen que cambiar QUE se ofrece, no solo el orden.

Esto existe porque una vez no fue asi. Con los pesos como simple multiplicador,
de 140 consultas (28 productos x 5 plazas) los tres modos daban exactamente el
mismo conjunto de sugerencias: cambiaba el orden y nada mas. Un panel que
promete "menos sugerencias, casi todas con ventas detras" y no recorta ninguna
es peor que no tener panel.
"""

import pytest

from app.recomendador.ranking import exigencia
from app.repositories import relaciones_repo
from app.services import recomendacion_service

MODOS = {
    "seguro": {"historico": 1.0, "atributos": 0.35, "manual": 1.5},
    "equilibrado": {"historico": 1.0, "atributos": 0.65, "manual": 1.5},
    "descubrir": {"historico": 0.7, "atributos": 1.0, "manual": 1.5},
}

PLAZAS = ("cdmx", "cancun", "merida", "chihuahua", "monterrey")


def aplicar(bd, pesos):
    bd.execute("BEGIN IMMEDIATE")
    relaciones_repo.guardar_pesos(bd, pesos)
    bd.commit()


def sugerencias(bd, modo):
    """{(sku, plaza): (skus complementarios)} para un modo."""
    aplicar(bd, MODOS[modo])
    skus = [f["sku"] for f in bd.execute("SELECT sku FROM productos ORDER BY sku")]
    return {
        (sku, plaza): tuple(
            c["sku"]
            for c in recomendacion_service.recomendar(bd, sku=sku, tienda=plaza)[
                "complementos"
            ]
        )
        for sku in skus
        for plaza in PLAZAS
    }


def test_exigir_mas_evidencia_recorta_y_exigir_menos_no(con_relaciones):
    """El orden de los tres modos es el que promete el panel."""
    bd = con_relaciones
    medias = {}
    for modo in MODOS:
        salida = sugerencias(bd, modo)
        medias[modo] = sum(len(v) for v in salida.values()) / len(salida)

    assert medias["seguro"] < medias["equilibrado"] < medias["descubrir"]


def test_cambiar_de_modo_cambia_que_se_ofrece_no_solo_el_orden(con_relaciones):
    bd = con_relaciones
    seguro = sugerencias(bd, "seguro")
    descubrir = sugerencias(bd, "descubrir")

    distinto_conjunto = sum(
        1 for clave in seguro if set(seguro[clave]) != set(descubrir[clave])
    )

    # Se afloja el numero exacto a proposito: lo que se fija es que sea
    # sustancial, no un valor que haya que retocar cada vez que cambia un dato.
    assert distinto_conjunto > len(seguro) * 0.5


def test_ningun_modo_deja_un_producto_sin_sugerencias(con_relaciones):
    """El corte es relativo al mejor candidato, asi que el mejor siempre pasa.

    Con un umbral absoluto, Merida -que no tiene un solo ticket- se quedaria en
    blanco en el modo exigente, que es justo el caso que el sistema debe cubrir.
    """
    bd = con_relaciones
    con_algo = {
        modo: sum(1 for v in sugerencias(bd, modo).values() if v) for modo in MODOS
    }

    assert con_algo["seguro"] == con_algo["descubrir"]


def test_el_modo_exigente_se_apoya_mas_en_ventas_reales(con_relaciones):
    bd = con_relaciones
    proporciones = {}
    for modo in ("seguro", "descubrir"):
        aplicar(bd, MODOS[modo])
        mostradas = respaldadas = 0
        skus = [f["sku"] for f in bd.execute("SELECT sku FROM productos")]
        for sku in skus:
            for complemento in recomendacion_service.recomendar(
                bd, sku=sku, tienda="cdmx"
            )["complementos"]:
                mostradas += 1
                respaldadas += bool(complemento["soporte"])
        proporciones[modo] = respaldadas / mostradas if mostradas else 0

    assert proporciones["seguro"] > proporciones["descubrir"]


@pytest.mark.parametrize(
    "pesos,esperado",
    [
        ({"historico": 1.0, "atributos": 0.35}, 0.65),
        ({"historico": 1.0, "atributos": 0.65}, 0.35),
        ({"historico": 0.7, "atributos": 1.0}, 0.0),
        # Sin historico configurado no hay nada con lo que ser exigente.
        ({"historico": 0.0, "atributos": 1.0}, 0.0),
    ],
)
def test_la_exigencia_sale_de_los_pesos(pesos, esperado):
    assert exigencia(pesos) == pytest.approx(esperado)


def test_la_sucursal_cambia_el_sustituto(con_relaciones):
    """Es el eje donde la plaza SI manda: el material que aguanta ahi.

    Los complementos no cambian con la plaza a proposito: responden a que
    trabajo esta haciendo el cliente, no al clima.
    """
    bd = con_relaciones
    aplicar(bd, MODOS["equilibrado"])
    skus = [f["sku"] for f in bd.execute("SELECT sku FROM productos ORDER BY sku")]

    cambian = 0
    for sku in skus:
        propuestos = set()
        for plaza in PLAZAS:
            sustituto = recomendacion_service.recomendar(bd, sku=sku, tienda=plaza)[
                "sustituto"
            ]
            propuestos.add(sustituto["sku"] if sustituto else None)
        cambian += len(propuestos) > 1

    assert cambian >= 10
