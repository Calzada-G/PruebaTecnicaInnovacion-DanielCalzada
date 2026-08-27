"""Contrato del diagnostico de plaza.

`nivel` es un Literal y no un texto libre a proposito: el panel pinta cada
hallazgo por su nivel, y un valor nuevo inventado en el servicio se traduciria
en una tarjeta sin color en vez de en un error.
"""

from typing import Literal

from pydantic import BaseModel, Field


class ProductoCitado(BaseModel):
    sku: str
    nombre: str


class Hallazgo(BaseModel):
    clave: str = Field(
        description="Identificador estable del tipo de hallazgo, p.ej. `nunca_vendido`."
    )
    nivel: Literal["alerta", "aviso", "oportunidad"] = Field(
        description="Con que color lo pinta el panel. Es cerrado a proposito."
    )
    titulo: str
    detalle: str
    accion: str = Field(
        description="Que hacer al respecto. Un diagnostico sin accion solo genera ansiedad."
    )
    total: int = Field(
        description="Productos afectados en total; `productos` trae solo los primeros."
    )
    productos: list[ProductoCitado] = []


class Diagnostico(BaseModel):
    tienda: str
    nombre: str
    perfil: str
    tickets_en_la_plaza: int
    tickets_en_la_cadena: int
    productos_activos: int
    hallazgos: list[Hallazgo] = []
