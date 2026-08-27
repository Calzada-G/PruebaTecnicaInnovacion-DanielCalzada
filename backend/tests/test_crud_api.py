"""Ciclo completo del CRUD por HTTP, tal como lo ejerce la interfaz.

test_crud.py prueba el servicio; esto prueba el contrato que consume el
frontend: codigos de estado, cuerpos de respuesta y, sobre todo, el efecto de
cada operacion sobre lo que el mostrador puede vender y recomendar.
"""

import pytest

from app.recomendador.historico import calcular_reglas
from app.repositories import relaciones_repo
from scripts.construir_relaciones import relaciones_por_atributos

NUEVO = {
    "sku": "SKU950",
    "nombre": "Disco de corte para metal 7",
    "descripcion": "Disco abrasivo para esmeriladora",
    "categoria": "consumible",
    "material": "oxido de aluminio",
    "uso_recomendado": "corte de metal en taller",
    "precio": 75.0,
    "stock": 20,
}


@pytest.fixture()
def con_relaciones(bd, cliente):
    """Cliente HTTP sobre una base que ya tiene las relaciones materializadas."""
    combinadas = {}
    for r in relaciones_por_atributos(bd) + calcular_reglas(bd):
        combinadas[(r["sku_origen"], r["sku_destino"], r["tipo"])] = r
    bd.execute("BEGIN IMMEDIATE")
    relaciones_repo.reemplazar(bd, list(combinadas.values()))
    bd.commit()
    return cliente


# --- CREAR ------------------------------------------------------------------


def test_crear_devuelve_201_y_el_producto_completo(cliente):
    respuesta = cliente.post("/api/productos", json=NUEVO)
    cuerpo = respuesta.json()

    assert respuesta.status_code == 201
    assert cuerpo["sku"] == "SKU950"
    assert cuerpo["precio"] == 75.0
    assert cuerpo["stock"] == 20
    assert cuerpo["activo"] is True


def test_lo_creado_aparece_de_inmediato_en_el_listado(cliente):
    cliente.post("/api/productos", json=NUEVO)

    listado = cliente.get("/api/productos").json()
    buscado = cliente.get("/api/productos?buscar=disco").json()

    assert any(p["sku"] == "SKU950" for p in listado)
    assert [p["sku"] for p in buscado] == ["SKU950"]


def test_lo_creado_se_puede_vender_en_el_acto(cliente):
    cliente.post("/api/productos", json=NUEVO)

    compra = cliente.post(
        "/api/compras",
        json={"tienda": "merida", "items": [{"sku": "SKU950", "cantidad": 3}]},
    )

    assert compra.status_code == 201
    assert cliente.get("/api/productos/SKU950").json()["stock"] == 17


def test_crear_rechaza_sku_duplicado_y_campos_invalidos(cliente):
    cliente.post("/api/productos", json=NUEVO)

    duplicado = cliente.post("/api/productos", json=NUEVO)
    sin_sku = cliente.post("/api/productos", json={**NUEVO, "sku": ""})
    precio_malo = cliente.post(
        "/api/productos", json={**NUEVO, "sku": "SKU951", "precio": -1}
    )
    stock_malo = cliente.post(
        "/api/productos", json={**NUEVO, "sku": "SKU952", "stock": -5}
    )

    assert duplicado.status_code == 409
    assert sin_sku.status_code == 422
    assert precio_malo.status_code == 422
    assert stock_malo.status_code == 422


def test_un_producto_nuevo_recibe_recomendaciones_sin_reconstruir_nada(
    con_relaciones,
):
    """Los complementos por atributos se calculan al servir, no al construir."""
    con_relaciones.post("/api/productos", json=NUEVO)

    respuesta = con_relaciones.get(
        "/api/recomendaciones?sku=SKU950&tienda=monterrey"
    )

    assert respuesta.status_code == 200
    # 'corte de metal en taller' lo clasifica como consumible de perforacion/
    # corte, asi que debe engancharse con EPP y herramienta del mismo trabajo.
    assert respuesta.json()["complementos"], "un alta nueva se quedo sin sugerencias"


# --- ACTUALIZAR -------------------------------------------------------------


def test_actualizar_solo_toca_lo_enviado(cliente):
    antes = cliente.get("/api/productos/SKU001").json()

    despues = cliente.patch("/api/productos/SKU001", json={"precio": 499.0}).json()

    assert despues["precio"] == 499.0
    assert despues["nombre"] == antes["nombre"]
    assert despues["stock"] == antes["stock"]
    assert despues["categoria"] == antes["categoria"]


def test_actualizar_permite_corregir_varios_campos_a_la_vez(cliente):
    despues = cliente.patch(
        "/api/productos/SKU001",
        json={"precio": 480.0, "stock": 33, "uso_recomendado": "corte fino"},
    ).json()

    assert (despues["precio"], despues["stock"]) == (480.0, 33)
    assert despues["uso_recomendado"] == "corte fino"


def test_subir_el_stock_desde_cero_devuelve_el_producto_al_mostrador(con_relaciones):
    con_relaciones.patch("/api/productos/SKU004", json={"stock": 0})
    sin_stock = con_relaciones.get(
        "/api/recomendaciones?sku=SKU001&tienda=monterrey"
    ).json()
    assert "SKU004" not in {c["sku"] for c in sin_stock["complementos"]}

    con_relaciones.patch("/api/productos/SKU004", json={"stock": 12})
    con_stock = con_relaciones.get(
        "/api/recomendaciones?sku=SKU001&tienda=monterrey"
    ).json()
    assert "SKU004" in {c["sku"] for c in con_stock["complementos"]}


def test_actualizar_valida_igual_que_crear(cliente):
    precio = cliente.patch("/api/productos/SKU001", json={"precio": -10})
    stock = cliente.patch("/api/productos/SKU001", json={"stock": -1})
    nombre = cliente.patch("/api/productos/SKU001", json={"nombre": ""})
    inexistente = cliente.patch("/api/productos/NO-EXISTE", json={"precio": 10})

    assert precio.status_code == 422
    assert stock.status_code == 422
    assert nombre.status_code == 422
    assert inexistente.status_code == 404


def test_actualizar_deja_rastro_en_el_libro_de_inventario(bd, cliente):
    cliente.patch("/api/productos/SKU001", json={"stock": 40})

    movimiento = bd.execute(
        """SELECT delta, stock_final, motivo FROM movimientos_inventario
            WHERE sku = 'SKU001' ORDER BY id DESC LIMIT 1"""
    ).fetchone()

    assert movimiento["motivo"] == "ajuste"
    assert movimiento["delta"] == 25
    assert movimiento["stock_final"] == 40


# --- ELIMINAR ---------------------------------------------------------------


def test_eliminar_devuelve_204_y_es_borrado_logico(cliente):
    respuesta = cliente.delete("/api/productos/SKU013")

    assert respuesta.status_code == 204
    # Sigue existiendo y consultable, pero marcado como inactivo.
    assert cliente.get("/api/productos/SKU013").json()["activo"] is False


def test_lo_eliminado_desaparece_del_listado_operativo_pero_no_del_administrativo(
    cliente,
):
    cliente.delete("/api/productos/SKU013")

    operativo = {p["sku"] for p in cliente.get("/api/productos").json()}
    administrativo = {
        p["sku"] for p in cliente.get("/api/productos?incluir_inactivos=true").json()
    }

    assert "SKU013" not in operativo
    assert "SKU013" in administrativo


def test_lo_eliminado_no_se_puede_vender_ni_recomendar(con_relaciones):
    antes = con_relaciones.get(
        "/api/recomendaciones?sku=SKU010&tienda=cdmx"
    ).json()
    assert "SKU012" in {c["sku"] for c in antes["complementos"]}

    con_relaciones.delete("/api/productos/SKU012")

    despues = con_relaciones.get(
        "/api/recomendaciones?sku=SKU010&tienda=cdmx"
    ).json()
    venta = con_relaciones.post(
        "/api/compras",
        json={"tienda": "cdmx", "items": [{"sku": "SKU012", "cantidad": 1}]},
    )

    assert "SKU012" not in {c["sku"] for c in despues["complementos"]}
    assert venta.status_code == 400


def test_eliminar_conserva_el_historial_de_ventas(bd, cliente):
    antes = bd.execute(
        "SELECT COUNT(*) c FROM ventas WHERE sku = 'SKU012'"
    ).fetchone()["c"]

    cliente.delete("/api/productos/SKU012")

    despues = bd.execute(
        "SELECT COUNT(*) c FROM ventas WHERE sku = 'SKU012'"
    ).fetchone()["c"]
    assert despues == antes > 0


def test_eliminar_un_sku_inexistente_da_404(cliente):
    assert cliente.delete("/api/productos/NO-EXISTE").status_code == 404


# --- CICLO COMPLETO ---------------------------------------------------------


def test_ciclo_completo_alta_edicion_baja_y_reactivacion(cliente):
    """El recorrido que hace un encargado en la vista de catalogo."""
    creado = cliente.post("/api/productos", json=NUEVO)
    assert creado.status_code == 201

    editado = cliente.patch(
        "/api/productos/SKU950", json={"precio": 89.0, "stock": 50}
    ).json()
    assert (editado["precio"], editado["stock"]) == (89.0, 50)

    assert cliente.delete("/api/productos/SKU950").status_code == 204
    assert cliente.get("/api/productos/SKU950").json()["activo"] is False

    # Reactivar es un PATCH de activo: es lo que hace el boton de deshacer.
    reactivado = cliente.patch("/api/productos/SKU950", json={"activo": True}).json()
    assert reactivado["activo"] is True
    assert reactivado["precio"] == 89.0

    vendible = cliente.post(
        "/api/compras",
        json={"tienda": "cancun", "items": [{"sku": "SKU950", "cantidad": 2}]},
    )
    assert vendible.status_code == 201
    assert cliente.get("/api/productos/SKU950").json()["stock"] == 48
