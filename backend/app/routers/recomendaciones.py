import sqlite3
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from ..db import obtener_bd
from ..schemas.error import RESPUESTAS
from ..schemas.recomendacion import Recomendacion
from ..services import recomendacion_service

router = APIRouter(prefix="/api/recomendaciones", tags=["recomendaciones"])


@router.get(
    "",
    response_model=Recomendacion,
    summary="Qué más ofrecer con este producto",
    responses=RESPUESTAS["producto_no_encontrado"] | RESPUESTAS["tienda_no_encontrada"],
)
def recomendar(
    bd: Annotated[sqlite3.Connection, Depends(obtener_bd)],
    sku: Annotated[
        str,
        Query(
            description="Producto ancla: lo que el cliente ya pidió en el mostrador."
        ),
    ],
    tienda: Annotated[
        str,
        Query(
            description=(
                "Sucursal. Aqui SI cambia el resultado: el sustituto depende "
                "del clima de la plaza, asi que el mismo SKU propone acero 316 "
                "en Cancun y acero al carbon en CDMX."
            )
        ),
    ],
    excluir: Annotated[
        str,
        Query(
            description=(
                "SKUs ya en el ticket, separados por coma. Nunca se recomiendan: "
                "ofrecer lo que el cliente ya lleva gasta el unico hueco que hay "
                "para proponer algo."
            )
        ),
    ] = "",
) -> dict:
    """Devuelve un sustituto para la plaza y hasta seis complementos.

    Se responde con `GET` y no con `POST` aunque el ticket viaje en la URL:
    es una lectura, sin efectos, y tiene que poder cachearse y repetirse.

    Nunca sale nada agotado, dado de baja, bloqueado por el negocio ni ya
    incluido en `excluir`. Ese filtro es duro, no una penalización de puntaje:
    un producto sin existencia no es una mala sugerencia, es una imposible.
    """
    return recomendacion_service.recomendar(
        bd,
        sku=sku,
        tienda=tienda,
        excluir={s.strip() for s in excluir.split(",") if s.strip()},
    )
