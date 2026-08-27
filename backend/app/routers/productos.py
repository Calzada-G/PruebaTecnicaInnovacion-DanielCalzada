import sqlite3

from fastapi import APIRouter, Depends, Query, Response, status

from ..db import obtener_bd
from ..schemas.producto import Producto, ProductoActualizar, ProductoCrear
from ..services import catalogo_service

router = APIRouter(prefix="/api/productos", tags=["productos"])


@router.get("", response_model=list[Producto])
def listar(
    q: str | None = None,
    tienda: str | None = None,
    incluir_inactivos: bool = Query(
        default=False,
        description="Solo para la vista de catalogo del negocio; el mostrador nunca lo usa.",
    ),
    bd: sqlite3.Connection = Depends(obtener_bd),
) -> list[dict]:
    return catalogo_service.listar(
        bd, q=q, tienda=tienda, incluir_inactivos=incluir_inactivos
    )


@router.get("/{sku}", response_model=Producto)
def obtener(sku: str, bd: sqlite3.Connection = Depends(obtener_bd)) -> dict:
    return catalogo_service.obtener(bd, sku)


@router.post("", response_model=Producto, status_code=status.HTTP_201_CREATED)
def crear(
    cuerpo: ProductoCrear, bd: sqlite3.Connection = Depends(obtener_bd)
) -> dict:
    return catalogo_service.crear(bd, cuerpo.model_dump())


@router.patch("/{sku}", response_model=Producto)
def actualizar(
    sku: str,
    cuerpo: ProductoActualizar,
    bd: sqlite3.Connection = Depends(obtener_bd),
) -> dict:
    return catalogo_service.actualizar(bd, sku, cuerpo.model_dump(exclude_unset=True))


@router.delete("/{sku}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar(sku: str, bd: sqlite3.Connection = Depends(obtener_bd)) -> Response:
    catalogo_service.eliminar(bd, sku)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
