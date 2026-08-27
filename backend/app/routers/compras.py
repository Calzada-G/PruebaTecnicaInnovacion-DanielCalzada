import sqlite3
from typing import Annotated

from fastapi import APIRouter, Depends, Header, status

from ..db import obtener_bd
from ..schemas.compra import CompraCrear, CompraRespuesta
from ..schemas.error import RESPUESTAS
from ..services import compra_service

router = APIRouter(prefix="/api/compras", tags=["compras"])


@router.post(
    "",
    response_model=CompraRespuesta,
    status_code=status.HTTP_201_CREATED,
    summary="Cobrar un ticket y descontar inventario",
    responses=RESPUESTAS["tienda_no_encontrada"] | RESPUESTAS["sin_existencia"],
)
def comprar(
    cuerpo: CompraCrear,
    bd: Annotated[sqlite3.Connection, Depends(obtener_bd)],
    idempotency_key: Annotated[
        str | None,
        Header(
            alias="Idempotency-Key",
            description=(
                "Identificador unico del INTENTO de cobro, generado por el "
                "cliente. Si llegan dos peticiones con la misma clave, la "
                "segunda devuelve el ticket original con `repetida: true` y no "
                "descuenta nada. Va en cabecera porque es metadato de "
                "transporte, no parte del ticket, igual que en cualquier "
                "pasarela de pago."
            ),
        ),
    ] = None,
) -> dict:
    """El ticket es atómico: si una línea no alcanza, no se descuenta ninguna.

    La comprobación de existencia vive dentro del `UPDATE ... WHERE stock >= ?`,
    no en un `SELECT` previo: entre leer y escribir cabe otra venta. Por eso el
    inventario no queda negativo ni con cobros simultáneos desde dos plazas.

    Las líneas repetidas del mismo SKU se suman antes de descontar: dos de 5
    contra 8 piezas fallan como una de 10, no cuelan 5 y luego 5.
    """
    return compra_service.comprar(
        bd,
        tienda=cuerpo.tienda,
        items=[i.model_dump() for i in cuerpo.items],
        clave_idempotencia=idempotency_key,
    )
