import sqlite3

from fastapi import APIRouter, Depends, Header, status

from ..db import obtener_bd
from ..schemas.compra import CompraCrear, CompraRespuesta
from ..services import compra_service

router = APIRouter(prefix="/api/compras", tags=["compras"])


@router.post("", response_model=CompraRespuesta, status_code=status.HTTP_201_CREATED)
def comprar(
    cuerpo: CompraCrear,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    bd: sqlite3.Connection = Depends(obtener_bd),
) -> dict:
    return compra_service.comprar(
        bd,
        tienda=cuerpo.tienda,
        items=[i.model_dump() for i in cuerpo.items],
        clave_idempotencia=idempotency_key,
    )
