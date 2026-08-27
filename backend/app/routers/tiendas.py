import sqlite3
from typing import Annotated

from fastapi import APIRouter, Depends

from ..db import obtener_bd
from ..repositories import tiendas_repo
from ..schemas.tienda import Tienda

router = APIRouter(prefix="/api/tiendas", tags=["tiendas"])


@router.get("", response_model=list[Tienda], summary="Las cinco sucursales")
def listar(bd: Annotated[sqlite3.Connection, Depends(obtener_bd)]) -> list[dict]:
    """Las plazas entre las que se opera, con su perfil y su color.

    Es la primera llamada de la interfaz: sin ella no se sabe en qué sucursal
    se está, y `tienda` es un parámetro obligatorio de casi todo lo demás.

    `perfil` es lo que hace que el mismo producto reciba distinta sugerencia en
    Cancún y en Chihuahua; `acento` es el color con el que se pinta la interfaz
    en esa plaza, para que nadie cobre en la sucursal equivocada.
    """
    return [dict(f) for f in tiendas_repo.listar(bd)]
