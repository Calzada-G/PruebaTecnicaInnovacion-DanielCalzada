import sqlite3
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from ..db import obtener_bd
from ..errores import RelacionNoEncontrada
from ..repositories import relaciones_repo

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
    return [dict(f) for f in relaciones_repo.listar(bd, tipo=tipo, fuente=fuente)]


@router.patch("/relaciones/{id_relacion}")
def ajustar(
    id_relacion: int,
    cuerpo: AjusteRelacion,
    bd: sqlite3.Connection = Depends(obtener_bd),
) -> dict:
    cambios = cuerpo.model_dump(exclude_unset=True)
    cur = bd.cursor()
    cur.execute("BEGIN IMMEDIATE")
    try:
        if relaciones_repo.obtener(bd, id_relacion) is None:
            raise RelacionNoEncontrada(id_relacion)
        if cambios:
            relaciones_repo.actualizar(bd, id_relacion, cambios)
        bd.commit()
    except Exception:
        bd.rollback()
        raise
    return dict(relaciones_repo.obtener(bd, id_relacion))


@router.get("/config/pesos")
def leer_pesos(bd: sqlite3.Connection = Depends(obtener_bd)) -> dict[str, float]:
    return relaciones_repo.pesos(bd)


@router.put("/config/pesos")
def guardar_pesos(
    cuerpo: PesosFuentes, bd: sqlite3.Connection = Depends(obtener_bd)
) -> dict[str, float]:
    cur = bd.cursor()
    cur.execute("BEGIN IMMEDIATE")
    try:
        relaciones_repo.guardar_pesos(bd, cuerpo.pesos)
        bd.commit()
    except Exception:
        bd.rollback()
        raise
    return relaciones_repo.pesos(bd)
