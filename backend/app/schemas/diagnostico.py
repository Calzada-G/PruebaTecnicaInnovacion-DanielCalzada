"""Contrato del diagnostico de plaza.

`nivel` es un Literal y no un texto libre a proposito: el panel pinta cada
hallazgo por su nivel, y un valor nuevo inventado en el servicio se traduciria
en una tarjeta sin color en vez de en un error.
"""

from typing import Literal

from pydantic import BaseModel


class ProductoCitado(BaseModel):
    sku: str
    nombre: str


class Hallazgo(BaseModel):
    clave: str
    nivel: Literal["alerta", "aviso", "oportunidad"]
    titulo: str
    detalle: str
    #: Que hacer al respecto. Un diagnostico sin accion solo genera ansiedad.
    accion: str
    #: Productos afectados en total; `productos` trae solo los primeros.
    total: int
    productos: list[ProductoCitado] = []


class Diagnostico(BaseModel):
    tienda: str
    nombre: str
    perfil: str
    tickets_en_la_plaza: int
    tickets_en_la_cadena: int
    productos_activos: int
    hallazgos: list[Hallazgo] = []
