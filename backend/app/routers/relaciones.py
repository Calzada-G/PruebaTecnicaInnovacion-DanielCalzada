import sqlite3
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from ..db import obtener_bd
from ..services import relaciones_service

router = APIRouter(prefix="/api", tags=["relaciones"])


class AjusteRelacion(BaseModel):
    estado: Literal["activa", "bloqueada", "fijada"] | None = None
    # None explicito borra el override y devuelve la relacion a su score calculado.
    peso_manual: float | None = Field(default=None, ge=0)


class PesosFuentes(BaseModel):
    pesos: dict[str, float]


@router.get("/relaciones")
def listar(
    tipo: str | None = None,
    fuente: str | None = None,
    bd: sqlite3.Connection = Depends(obtener_bd),
) -> list[dict]:
    return relaciones_service.listar(bd, tipo=tipo, fuente=fuente)


@router.patch("/relaciones/{id_relacion}")
def ajustar(
    id_relacion: int,
    cuerpo: AjusteRelacion,
    bd: sqlite3.Connection = Depends(obtener_bd),
) -> dict:
    return relaciones_service.ajustar(
        bd, id_relacion, cuerpo.model_dump(exclude_unset=True)
    )


@router.get("/config/pesos")
def leer_pesos(bd: sqlite3.Connection = Depends(obtener_bd)) -> dict[str, float]:
    return relaciones_service.leer_pesos(bd)


@router.put("/config/pesos")
def guardar_pesos(
    cuerpo: PesosFuentes, bd: sqlite3.Connection = Depends(obtener_bd)
) -> dict[str, float]:
    return relaciones_service.guardar_pesos(bd, cuerpo.pesos)
