from pydantic import BaseModel, ConfigDict, Field


class ItemCompra(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    sku: str = Field(min_length=1)
    cantidad: int = Field(gt=0)


class CompraCrear(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    tienda: str = Field(min_length=1)
    items: list[ItemCompra] = Field(min_length=1)


class LineaTicket(BaseModel):
    sku: str
    nombre: str
    cantidad: int
    precio_unitario: float
    subtotal: float
    stock_restante: int


class CompraRespuesta(BaseModel):
    ticket_id: str
    tienda: str
    fecha: str
    lineas: list[LineaTicket]
    total: float
    # True cuando la peticion se resolvio con una Idempotency-Key ya vista y no
    # se descontó nada: el mostrador lo usa para no avisar de un cobro doble.
    repetida: bool = False
