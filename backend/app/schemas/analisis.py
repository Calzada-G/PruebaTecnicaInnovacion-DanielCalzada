"""Contrato del analisis con IA."""

from typing import Literal

from pydantic import BaseModel, Field


class PuntoAnalisis(BaseModel):
    titulo: str
    analisis: str = Field(description="Que significa y que implica.")
    dato: str = Field(description="El numero concreto en el que se apoya.")
    impacto: Literal["alto", "medio", "bajo"]
    skus: list[str] = []


class Decision(BaseModel):
    titulo: str
    porque: str
    accion: str


class Analisis(BaseModel):
    resumen: str
    negocio: list[PuntoAnalisis] = Field(
        default=[], description="Lectura de las ventas, el inventario y la plaza."
    )
    sistema: list[PuntoAnalisis] = Field(
        default=[],
        description="Si el motor de recomendaciones puede trabajar en esta sucursal.",
    )
    decisiones: list[Decision] = []


class RespuestaAnalisis(BaseModel):
    tienda: str
    disponible: bool = Field(
        description="Hay GEMINI_API_KEY configurada. Si no, el resto sigue igual."
    )
    hay_analisis: bool
    huella_actual: str = Field(
        description=(
            "Identifica el estado del sistema ahora mismo: catalogo, existencias, "
            "ventas, relaciones y pesos. Cambia cuando cambia cualquiera de ellos."
        )
    )
    vigente: bool = Field(
        default=False,
        description=(
            "El analisis guardado describe el sistema actual. Mientras sea true no "
            "hay nada nuevo que analizar y pedirlo no gasta una llamada."
        ),
    )
    desde_cache: bool = Field(
        default=False, description="Se devolvio lo guardado, sin consultar al modelo."
    )
    analisis: Analisis | None = None
    modelo: str | None = None
    generado_en: str | None = None
    huella: str | None = Field(
        default=None, description="Estado del sistema que se analizo."
    )
