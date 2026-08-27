import sqlite3
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query

from ..db import obtener_bd
from ..schemas.error import RESPUESTAS
from ..schemas.recomendacion import RelacionSalida
from ..schemas.relacion import AjusteRelacion, PesosFuentes
from ..services import relaciones_service

router = APIRouter(prefix="/api", tags=["relaciones"])

Conexion = Annotated[sqlite3.Connection, Depends(obtener_bd)]


@router.get(
    "/relaciones",
    response_model=list[RelacionSalida],
    summary="Todo lo que el sistema sabe sugerir",
)
def listar(
    bd: Conexion,
    tipo: Annotated[
        str | None,
        Query(description="`complemento` (va junto) o `sustituto` (va en lugar de)."),
    ] = None,
    fuente: Annotated[
        str | None,
        Query(
            description=(
                "`historico` si sale de tickets reales, `atributos` si sale del "
                "tipo de producto y del clima de la plaza, `manual` si la puso "
                "una persona."
            )
        ),
    ] = None,
) -> list[dict]:
    """El catálogo auditable de sugerencias, con el porqué de cada una.

    Es la misma tabla que consulta el mostrador, no un informe aparte: lo que
    se bloquea o se fija aquí cambia lo que se ofrece al cliente sin reiniciar
    nada. Cada fila trae su evidencia (tickets, confianza, lift) y el texto que
    el vendedor puede repetirle al cliente.
    """
    return relaciones_service.listar(bd, tipo=tipo, fuente=fuente)


@router.patch(
    "/relaciones/{id_relacion}",
    response_model=RelacionSalida,
    summary="Bloquear, fijar o repesar una sugerencia",
    responses=RESPUESTAS["relacion_no_encontrada"],
)
def ajustar(
    cuerpo: AjusteRelacion,
    bd: Conexion,
    id_relacion: Annotated[
        int, Path(description="Id de la relación, tal como lo devuelve el listado.")
    ],
) -> dict:
    """La decisión del negocio sobrevive a reconstruir las reglas.

    `estado` vale `activa`, `bloqueada` (no se ofrece nunca más) o `fijada`
    (se ofrece siempre primero). `peso_manual` sustituye al puntaje calculado;
    mandarlo a `null` devuelve la relación a lo que diga el algoritmo.

    Responde exactamente la misma forma que el listado, para que el cliente no
    tenga que volver a pedirlo ni mantener dos representaciones de lo mismo.
    """
    return relaciones_service.ajustar(
        bd, id_relacion, cuerpo.model_dump(exclude_unset=True)
    )


@router.get(
    "/config/pesos",
    response_model=dict[str, float],
    summary="Cuánto pesa hoy cada fuente",
)
def leer_pesos(bd: Conexion) -> dict[str, float]:
    """Un mapa `fuente → peso`, no una lista de campos fijos.

    El recomendador se declara con el patrón Strategy: añadir una fuente nueva
    —temporada, promociones— es añadir una clase, y esta configuración tiene
    que admitirla sin cambiar el contrato ni migrar la tabla.
    """
    return relaciones_service.leer_pesos(bd)


@router.put(
    "/config/pesos",
    response_model=dict[str, float],
    summary="Cambiar el peso de las fuentes",
)
def guardar_pesos(cuerpo: PesosFuentes, bd: Conexion) -> dict[str, float]:
    """PUT y no PATCH: se manda el estado completo de la configuración.

    Son dos o tres números que se ajustan juntos y significan algo *en
    relación* entre sí; mandarlos de uno en uno dejaría estados intermedios
    sin sentido. 0 apaga una fuente, 1 es su peso natural.
    """
    return relaciones_service.guardar_pesos(bd, cuerpo.pesos)
