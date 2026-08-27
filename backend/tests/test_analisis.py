"""El analisis con IA: una llamada, y solo si hay algo nuevo que analizar.

Ninguno de estos tests toca la red. Lo que se prueba no es que el modelo
escriba bien -eso no es testeable- sino las dos garantias que si lo son: que
no se llama dos veces por lo mismo, y que lo que devuelva no puede romper nada.
"""

import pytest

from app.errores import IANoDisponible
from app.ia import analista
from app.services import analisis_service, catalogo_service

RESPUESTA = {
    "resumen": "La plaza vende poco y tiene inventario parado.",
    "negocio": [
        {
            "titulo": "Inventario sin rotacion",
            "analisis": "Hay mucho valor detenido en productos que no salen.",
            "dato": "290450 en catalogo",
            "impacto": "alto",
            "skus": ["SKU018"],
        }
    ],
    "sistema": [
        {
            "titulo": "Sin historico propio",
            "analisis": "Todo lo que propone sale de atributos.",
            "dato": "0 tickets",
            "impacto": "alto",
            "skus": [],
        }
    ],
    "decisiones": [
        {"titulo": "Registrar ventas", "porque": "No hay datos.", "accion": "Cobrar aqui."}
    ],
}


@pytest.fixture()
def modelo(monkeypatch):
    """Sustituye la llamada al modelo y cuenta cuantas veces se pide."""
    llamadas = []

    def falso(retrato):
        llamadas.append(retrato)
        return RESPUESTA

    monkeypatch.setattr(analisis_service.analista, "analizar", falso)
    monkeypatch.setattr(analisis_service.cliente, "hay_clave", lambda: True)
    return llamadas


def test_la_segunda_peticion_no_consulta_al_modelo(con_relaciones, modelo):
    """La garantia central: preguntar lo mismo no gasta cuota."""
    bd = con_relaciones

    primera = analisis_service.generar(bd, "merida")
    segunda = analisis_service.generar(bd, "merida")

    assert len(modelo) == 1
    assert primera["desde_cache"] is False
    assert segunda["desde_cache"] is True
    assert segunda["analisis"] == primera["analisis"]


def test_cambiar_el_catalogo_vuelve_a_habilitar_el_analisis(con_relaciones, modelo):
    bd = con_relaciones
    analisis_service.generar(bd, "merida")
    assert analisis_service.consultar(bd, "merida")["vigente"] is True

    catalogo_service.actualizar(bd, "SKU010", {"precio": 99.0})

    assert analisis_service.consultar(bd, "merida")["vigente"] is False
    analisis_service.generar(bd, "merida")
    assert len(modelo) == 2


def test_una_venta_tambien_invalida_el_analisis(con_relaciones, modelo):
    """Vender es informacion nueva: el analisis anterior ya no describe esto."""
    from app.services import compra_service

    bd = con_relaciones
    analisis_service.generar(bd, "merida")
    compra_service.comprar(bd, "merida", [{"sku": "SKU001", "cantidad": 1}])

    assert analisis_service.consultar(bd, "merida")["vigente"] is False


def test_cada_plaza_tiene_su_propio_analisis(con_relaciones, modelo):
    bd = con_relaciones
    analisis_service.generar(bd, "merida")
    analisis_service.generar(bd, "cdmx")

    assert len(modelo) == 2
    assert modelo[0]["plaza"]["nombre"] != modelo[1]["plaza"]["nombre"]


def test_consultar_nunca_llama_al_modelo(con_relaciones, modelo):
    bd = con_relaciones

    respuesta = analisis_service.consultar(bd, "merida")

    assert modelo == []
    assert respuesta["hay_analisis"] is False
    assert respuesta["vigente"] is False


def test_sin_clave_no_se_guarda_nada(con_relaciones, monkeypatch):
    bd = con_relaciones
    monkeypatch.setattr(
        analisis_service.cliente, "hay_clave", lambda: False
    )

    def sin_clave(_):
        raise IANoDisponible("No hay GEMINI_API_KEY configurada.")

    monkeypatch.setattr(analisis_service.analista, "analizar", sin_clave)

    with pytest.raises(IANoDisponible):
        analisis_service.generar(bd, "merida")

    assert analisis_service.consultar(bd, "merida")["hay_analisis"] is False


def test_el_retrato_lleva_las_cuentas_hechas(con_relaciones, modelo):
    """Un modelo sumando columnas se equivoca; explicando una suma, no."""
    bd = con_relaciones
    analisis_service.generar(bd, "merida")
    retrato = modelo[0]

    assert retrato["plaza"]["tickets_aqui"] == 0
    assert retrato["inventario"]["valor_total"] > 0
    assert retrato["ventas_de_esta_plaza"]["participacion_en_unidades_pct"] == 0.0
    assert retrato["sistema_de_recomendacion"]["relaciones_totales"] > 0
    # El diagnostico determinista viaja tambien, para que no lo repita.
    assert retrato["ya_detectado_automaticamente"]


def test_una_respuesta_desbordada_del_modelo_se_recorta(monkeypatch):
    """El modelo puede devolver quince puntos de mil caracteres. No pasa."""
    monkeypatch.setattr(
        analista,
        "pedir_json",
        lambda *_, **__: {
            "resumen": "x" * 5000,
            "negocio": [
                {
                    "titulo": "t" * 500,
                    "analisis": "a" * 5000,
                    "dato": "d" * 500,
                    "impacto": "catastrofico",
                    "skus": [f"SKU{i:03d}" for i in range(20)],
                }
            ]
            * 15,
            "sistema": [{"titulo": "sin analisis"}],
            "decisiones": [{"titulo": "sin accion"}],
        },
    )

    salida = analista.analizar({})

    assert len(salida["resumen"]) <= 600
    assert len(salida["negocio"]) == analista.MAXIMO_PUNTOS
    assert len(salida["negocio"][0]["titulo"]) <= analista.LARGO_TITULO
    assert len(salida["negocio"][0]["skus"]) <= 6
    # Impacto inventado cae a "medio" en vez de colarse a la interfaz.
    assert salida["negocio"][0]["impacto"] == "medio"
    # Sin analisis o sin accion, el punto no aporta y se descarta.
    assert salida["sistema"] == []
    assert salida["decisiones"] == []
