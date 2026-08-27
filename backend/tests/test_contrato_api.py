"""Contrato HTTP: codigo de estado y forma del JSON de cada ruta.

Los demas tests comprueban el comportamiento; este fija el contrato que consume
el frontend. Si alguien cambia un 404 por un 200, o convierte un booleano en
entero, aqui se rompe antes de llegar a la interfaz.
"""

import pytest

PRODUCTO = {
    "sku": "SKU777",
    "nombre": "Producto de contrato",
    "categoria": "consumible",
    "precio": 10.0,
    "stock": 5,
}

# (metodo, ruta, cuerpo, estado esperado). El orden importa: crear va antes de
# duplicar, y eliminar despues de actualizar.
RUTAS = [
    ("GET", "/api/tiendas", None, 200),
    ("GET", "/api/productos", None, 200),
    ("GET", "/api/productos/SKU001", None, 200),
    ("GET", "/api/productos/NO-EXISTE", None, 404),
    ("POST", "/api/productos", PRODUCTO, 201),
    ("POST", "/api/productos", PRODUCTO, 409),
    ("POST", "/api/productos", {**PRODUCTO, "sku": "CON ESPACIO"}, 422),
    ("POST", "/api/productos", {**PRODUCTO, "sku": "SKU778", "precio": -1}, 422),
    ("PATCH", "/api/productos/SKU777", {"precio": 20.0}, 200),
    ("PATCH", "/api/productos/SKU777", {"precio": -5}, 422),
    ("PATCH", "/api/productos/NO-EXISTE", {"precio": 1.0}, 404),
    ("DELETE", "/api/productos/SKU777", None, 204),
    ("DELETE", "/api/productos/NO-EXISTE", None, 404),
    ("GET", "/api/recomendaciones?sku=SKU001&tienda=cdmx", None, 200),
    ("GET", "/api/recomendaciones?sku=NO-EXISTE&tienda=cdmx", None, 404),
    ("GET", "/api/recomendaciones?sku=SKU001&tienda=narnia", None, 404),
    ("GET", "/api/recomendaciones?tienda=cdmx", None, 422),
    ("POST", "/api/compras", {"tienda": "cdmx", "items": [{"sku": "SKU001", "cantidad": 1}]}, 201),
    ("POST", "/api/compras", {"tienda": "cdmx", "items": [{"sku": "SKU001", "cantidad": 9999}]}, 409),
    ("POST", "/api/compras", {"tienda": "narnia", "items": [{"sku": "SKU001", "cantidad": 1}]}, 404),
    ("POST", "/api/compras", {"tienda": "cdmx", "items": []}, 422),
    ("POST", "/api/compras", {"tienda": "cdmx", "items": [{"sku": "SKU001", "cantidad": 0}]}, 422),
    ("GET", "/api/relaciones", None, 200),
    ("PATCH", "/api/relaciones/999999", {"estado": "activa"}, 404),
    ("GET", "/api/config/pesos", None, 200),
    ("PUT", "/api/config/pesos", {"pesos": {"historico": 1.0}}, 200),
]


def test_todas_las_rutas_devuelven_el_estado_esperado(cliente):
    fallos = []
    for metodo, ruta, cuerpo, esperado in RUTAS:
        respuesta = cliente.request(metodo, ruta, json=cuerpo)
        if respuesta.status_code != esperado:
            fallos.append(f"{metodo} {ruta}: esperado {esperado}, dio {respuesta.status_code}")
    assert not fallos, "\n".join(fallos)


def test_el_error_de_validacion_trae_un_mensaje_legible(cliente):
    """El frontend convierte la lista de Pydantic en un texto; debe haberlo."""
    respuesta = cliente.post("/api/productos", json={**PRODUCTO, "sku": "MAL SKU"})
    detalle = respuesta.json()["detail"]

    assert respuesta.status_code == 422
    assert isinstance(detalle, list) and detalle
    assert all("msg" in error and "loc" in error for error in detalle)


def test_el_error_de_stock_trae_sku_y_disponible(cliente):
    """Sin estos dos campos el mostrador no puede decir 'Quedan 8'."""
    respuesta = cliente.post(
        "/api/compras",
        json={"tienda": "cdmx", "items": [{"sku": "SKU027", "cantidad": 999}]},
    )
    cuerpo = respuesta.json()

    assert respuesta.status_code == 409
    assert cuerpo["sku"] == "SKU027"
    assert cuerpo["disponible"] == 8
    assert isinstance(cuerpo["detail"], str)


@pytest.mark.parametrize(
    "ruta,campos",
    [
        (
            "/api/productos/SKU001",
            {
                "sku", "nombre", "descripcion", "categoria", "material",
                "uso_recomendado", "precio", "stock", "activo",
            },
        ),
        ("/api/tiendas", {"id", "nombre", "perfil", "acento"}),
    ],
)
def test_el_json_expone_exactamente_los_campos_del_contrato(cliente, ruta, campos):
    cuerpo = cliente.get(ruta).json()
    objeto = cuerpo[0] if isinstance(cuerpo, list) else cuerpo
    assert set(objeto) == campos


def test_activo_viaja_como_booleano_en_todos_los_endpoints(bd, cliente):
    """El mismo concepto no puede ser bool en una ruta y 0/1 en otra."""
    from app.recomendador.historico import calcular_reglas
    from app.repositories import relaciones_repo
    from scripts.construir_relaciones import relaciones_por_atributos

    combinadas = {}
    for r in relaciones_por_atributos(bd) + calcular_reglas(bd):
        combinadas[(r["sku_origen"], r["sku_destino"], r["tipo"])] = r
    bd.execute("BEGIN IMMEDIATE")
    relaciones_repo.reemplazar(bd, list(combinadas.values()))
    bd.commit()

    producto = cliente.get("/api/productos/SKU001").json()
    relacion = cliente.get("/api/relaciones").json()[0]

    assert isinstance(producto["activo"], bool)
    assert isinstance(relacion["activo_destino"], bool)


def test_el_patch_de_relaciones_devuelve_la_misma_forma_que_el_listado(bd, cliente):
    from app.recomendador.historico import calcular_reglas
    from app.repositories import relaciones_repo
    from scripts.construir_relaciones import relaciones_por_atributos

    combinadas = {}
    for r in relaciones_por_atributos(bd) + calcular_reglas(bd):
        combinadas[(r["sku_origen"], r["sku_destino"], r["tipo"])] = r
    bd.execute("BEGIN IMMEDIATE")
    relaciones_repo.reemplazar(bd, list(combinadas.values()))
    bd.commit()

    del_listado = cliente.get("/api/relaciones").json()[0]
    del_patch = cliente.patch(
        f"/api/relaciones/{del_listado['id']}", json={"estado": "fijada"}
    ).json()

    assert set(del_patch) == set(del_listado)
    assert del_patch["estado"] == "fijada"
