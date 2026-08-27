"""Contrato comun de las fuentes de recomendacion.

Agregar una fuente nueva (un modelo, una API externa, reglas de temporada) es
agregar una clase que cumpla FuenteRecomendacion. Ni el ranking ni la API se
tocan: solo cambia la lista que recibe ranking.mezclar.
"""

from dataclasses import dataclass
from typing import Literal, Protocol

TipoRelacion = Literal["complemento", "sustituto"]


@dataclass(frozen=True)
class Candidato:
    sku: str
    tipo: TipoRelacion
    # Normalizado 0..1 dentro de cada fuente. La comparacion entre fuentes la
    # hace ranking.py multiplicando por el peso configurado, no la fuente.
    score: float
    fuente: str
    justificacion: str
    soporte: int | None = None
    confianza: float | None = None
    lift: float | None = None


class FuenteRecomendacion(Protocol):
    nombre: str

    def generar(self, sku: str, tienda: str) -> list[Candidato]: ...
