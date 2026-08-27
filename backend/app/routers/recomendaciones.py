import sqlite3

from fastapi import APIRouter, Depends, Query

from ..db import obtener_bd
from ..schemas.recomendacion import Recomendacion
from ..services import recomendacion_service

router = APIRouter(prefix="/api/recomendaciones", tags=["recomendaciones"])


@router.get("", response_model=Recomendacion)
def recomendar(
    sku: str,
    tienda: str,
    excluir: str = Query(
        default="",
        description="SKUs ya en el ticket, separados por coma. Nunca se recomiendan.",
    ),
    bd: sqlite3.Connection = Depends(obtener_bd),
) -> dict:
    return recomendacion_service.recomendar(
        bd,
        sku=sku,
        tienda=tienda,
        excluir={s.strip() for s in excluir.split(",") if s.strip()},
    )
