"""Contrato del estado de la API.

Los conteos van anidados bajo `contenido` y no sueltos en la raiz: en la raiz,
`productos: 28` al lado de `version: "0.1.0"` no dice si son 28 productos o el
producto numero 28. Agrupados, se leen como lo que son.
"""

from typing import Literal

from pydantic import BaseModel, Field


class ContenidoBase(BaseModel):
    """Que hay dentro de la base ahora mismo."""

    tiendas: int
    productos_activos: int
    tickets: int
    relaciones: int
    relaciones_redactadas_por_ia: int = Field(
        description="De esas relaciones, cuantas tienen ya el texto escrito por el LLM."
    )


class Salud(BaseModel):
    estado: Literal["listo", "base vacia", "sin base de datos"] = Field(
        description=(
            "`base vacia` significa que falta correr el seed; "
            "`sin base de datos`, que el archivo no existe o no tiene tablas."
        )
    )
    version: str
    base_de_datos: str = Field(description="Ruta del archivo SQLite en uso.")
    origenes_cors: list[str] = Field(
        description="Origenes que el navegador tiene permitido usar contra esta API."
    )
    contenido: ContenidoBase | None = Field(
        default=None, description="Ausente si la base todavia no existe o no esta sembrada."
    )
