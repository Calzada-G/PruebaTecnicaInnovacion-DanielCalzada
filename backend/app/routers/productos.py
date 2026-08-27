import sqlite3
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Response, status

from ..db import obtener_bd
from ..schemas.error import RESPUESTAS
from ..schemas.producto import Producto, ProductoActualizar, ProductoCrear
from ..services import catalogo_service

router = APIRouter(prefix="/api/productos", tags=["productos"])

# Annotated y no un valor por defecto: asi el orden de los parametros lo decide
# la legibilidad de la firma y no la regla de Python sobre argumentos con default.
ClaveSku = Annotated[
    str, Path(description="Clave del producto, tal como se guarda: SKU001.")
]
Conexion = Annotated[sqlite3.Connection, Depends(obtener_bd)]


@router.get(
    "",
    response_model=list[Producto],
    summary="Buscar en el catálogo",
    responses=RESPUESTAS["tienda_no_encontrada"],
)
def listar(
    bd: Conexion,
    buscar: Annotated[
        str | None,
        Query(
            description=(
                "Texto libre. Busca a la vez en nombre, SKU, categoria, material "
                "y uso recomendado, que es lo que permite encontrar por «salino» "
                "o por «interior» y no solo por el nombre comercial."
            )
        ),
    ] = None,
    tienda: Annotated[
        str | None,
        Query(
            description=(
                "Sucursal desde la que se consulta. NO filtra: el inventario es "
                "compartido y el stock es el mismo en las cinco. Lo que cambia "
                "es el ORDEN, que pone delante lo que mas se mueve en esa plaza."
            )
        ),
    ] = None,
    incluir_inactivos: Annotated[
        bool,
        Query(
            description=(
                "Incluye los productos dados de baja. Solo lo usa la vista de "
                "catalogo, donde la baja tiene que poder revertirse; el "
                "mostrador nunca lo manda, porque eso no se vende."
            )
        ),
    ] = False,
) -> list[dict]:
    """Catálogo vendible, ordenado según la plaza que pregunta."""
    return catalogo_service.listar(
        bd, buscar=buscar, tienda=tienda, incluir_inactivos=incluir_inactivos
    )


@router.get(
    "/{sku}",
    response_model=Producto,
    summary="Ficha de un producto",
    responses=RESPUESTAS["producto_no_encontrado"],
)
def obtener(sku: ClaveSku, bd: Conexion) -> dict:
    """Devuelve también los dados de baja: la ficha existe aunque no se venda."""
    return catalogo_service.obtener(bd, sku)


@router.post(
    "",
    response_model=Producto,
    status_code=status.HTTP_201_CREATED,
    summary="Dar de alta un producto",
    responses=RESPUESTAS["sku_duplicado"],
)
def crear(cuerpo: ProductoCrear, bd: Conexion) -> dict:
    """Alta con existencia inicial, que queda como primer movimiento de inventario."""
    return catalogo_service.crear(bd, cuerpo.model_dump())


@router.patch(
    "/{sku}",
    response_model=Producto,
    summary="Corregir precio, existencia u otros campos",
    responses=RESPUESTAS["producto_no_encontrado"],
)
def actualizar(sku: ClaveSku, cuerpo: ProductoActualizar, bd: Conexion) -> dict:
    """PATCH y no PUT: la edición del catálogo es parcial.

    Solo se tocan los campos presentes en el cuerpo, así que dos personas
    corrigiendo cosas distintas del mismo producto no se pisan. Un cambio de
    existencia queda registrado como ajuste de almacén.
    """
    return catalogo_service.actualizar(bd, sku, cuerpo.model_dump(exclude_unset=True))


@router.delete(
    "/{sku}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Dar de baja un producto",
    responses=RESPUESTAS["producto_no_encontrado"],
)
def eliminar(sku: ClaveSku, bd: Conexion) -> Response:
    """Baja lógica: el SKU sigue existiendo, deja de venderse y de recomendarse.

    Nunca se borra la fila porque `ventas` y `movimientos_inventario` la
    referencian; borrarla rompería el historial. Se revierte con
    `PATCH {"activo": true}`.

    Es idempotente: repetirlo sobre un producto ya dado de baja vuelve a
    responder 204. Dos pestañas abiertas no deberían dar resultados distintos
    cuando el efecto buscado ya se cumplió.
    """
    catalogo_service.eliminar(bd, sku)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
