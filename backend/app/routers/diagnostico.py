import sqlite3

from fastapi import APIRouter, Depends, Query

from ..db import obtener_bd
from ..schemas.diagnostico import Diagnostico
from ..services import diagnostico_service

router = APIRouter(prefix="/api/diagnostico", tags=["diagnostico"])


@router.get("", response_model=Diagnostico)
def diagnosticar(
    tienda: str = Query(description="Slug de la sucursal a revisar."),
    bd: sqlite3.Connection = Depends(obtener_bd),
) -> dict:
    """Que no esta funcionando en esta plaza y que conviene hacer."""
    return diagnostico_service.diagnosticar(bd, tienda)
