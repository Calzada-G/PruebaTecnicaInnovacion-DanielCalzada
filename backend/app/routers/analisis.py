import sqlite3
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from ..db import obtener_bd
from ..schemas.analisis import RespuestaAnalisis
from ..schemas.error import RESPUESTAS, respuesta
from ..services import analisis_service

router = APIRouter(prefix="/api/analisis", tags=["analisis"])

Conexion = Annotated[sqlite3.Connection, Depends(obtener_bd)]


class PeticionAnalisis(BaseModel):
    tienda: str


@router.get(
    "",
    response_model=RespuestaAnalisis,
    summary="Leer el análisis guardado",
    responses=RESPUESTAS["tienda_no_encontrada"],
)
def consultar(
    bd: Conexion,
    tienda: Annotated[str, Query(description="Sucursal.")],
) -> dict:
    """Devuelve lo último que se analizó. **Nunca consulta al modelo.**

    `vigente` dice si ese análisis sigue describiendo el sistema actual: se
    compara la huella del estado de ahora con la del momento en que se generó.
    Es lo que permite que el botón se apague solo cuando no hay nada nuevo.
    """
    return analisis_service.consultar(bd, tienda)


@router.post(
    "",
    response_model=RespuestaAnalisis,
    summary="Analizar el sistema con IA",
    responses=RESPUESTAS["tienda_no_encontrada"]
    | {503: respuesta("El modelo no está disponible: sin clave, sin red o respuesta ilegible.")},
)
def generar(cuerpo: PeticionAnalisis, bd: Conexion) -> dict:
    """Una sola llamada al modelo, y solo si el sistema cambió.

    Antes de preguntar se calcula la huella del estado —catálogo, existencias,
    ventas, relaciones, ajustes del negocio y pesos—. Si coincide con la del
    último análisis guardado, **se devuelve ese con `desde_cache: true` y no se
    consume ni un token**. La garantía vive en el servidor, no en el botón: así
    no depende de que el cliente se acuerde de comprobarlo.

    Es `POST` y no `GET` porque puede tener efectos: gasta cuota y escribe una
    fila. `GET /api/analisis` es la lectura pura.

    El modelo **no decide qué se recomienda**. El ranking sigue siendo
    determinista y evaluable; esto es una lectura del negocio, guardada y
    etiquetada como opinión de un modelo.
    """
    return analisis_service.generar(bd, cuerpo.tienda)
