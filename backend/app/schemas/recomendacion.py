from pydantic import BaseModel


class CandidatoSalida(BaseModel):
    sku: str
    tipo: str
    score: float
    fuente: str
    justificacion: str
    # Solo vienen de la fuente historica; por atributos no hay tickets que citar.
    soporte: int | None = None
    confianza: float | None = None
    lift: float | None = None


class Recomendacion(BaseModel):
    sustituto: CandidatoSalida | None = None
    complementos: list[CandidatoSalida] = []
