import sqlite3
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from ..db import obtener_bd
from ..schemas.diagnostico import Diagnostico
from ..schemas.error import RESPUESTAS
from ..services import diagnostico_service

router = APIRouter(prefix="/api/diagnostico", tags=["diagnostico"])


@router.get(
    "",
    response_model=Diagnostico,
    summary="Qué no está funcionando en esta plaza",
    responses=RESPUESTAS["tienda_no_encontrada"],
)
def diagnosticar(
    bd: Annotated[sqlite3.Connection, Depends(obtener_bd)],
    tienda: Annotated[
        str, Query(description="Sucursal a revisar. Cada plaza da un resultado distinto.")
    ],
) -> dict:
    """La única ruta que responde algo que nadie preguntó.

    El resto de la API contesta peticiones del usuario; esta le dice a la
    sucursal lo que no sabe que le pasa: qué no se ha vendido nunca, qué se
    vende en otras plazas y aquí no, qué se agotó, qué material no aguanta el
    clima de la zona y qué producto convendría dar de alta.

    Todo sale de datos que ya existen —`ventas`, `productos`, `relaciones`—.
    No hay ningún caso especial escrito a mano: si Mérida sale distinta es
    porque no tiene tickets, y el aviso desaparece solo en cuanto los tenga.

    Cada hallazgo trae su `accion`. Un diagnóstico sin qué-hacer solo genera
    ansiedad y a la tercera vez se ignora.
    """
    return diagnostico_service.diagnosticar(bd, tienda)
