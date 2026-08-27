"""Contrato de una sucursal."""

from pydantic import BaseModel, Field


class Tienda(BaseModel):
    id: str = Field(
        description="Slug ASCII: `cancun`, no `Cancún`. Es lo que viaja en las URLs."
    )
    nombre: str = Field(description="Con acentos. Solo para mostrar.")
    perfil: str = Field(
        description=(
            "Condiciones de la plaza: `costero_salino`, `sol_directo_seco`, "
            "`interior_urbano` o `taller_metalmecanico`. Decide que sustituto se "
            "propone, y es lo que permite recomendar en una sucursal sin historico."
        )
    )
    acento: str = Field(
        description=(
            "Color de la interfaz en esa sucursal. No es decoracion: evita cobrar "
            "en la plaza equivocada."
        )
    )
