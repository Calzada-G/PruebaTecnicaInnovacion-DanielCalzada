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


class RelacionSalida(BaseModel):
    """Una relacion tal como la ve el panel del negocio.

    Existe para que el contrato quede documentado en /docs y, sobre todo, para
    que `activo_destino` salga como booleano igual que `Producto.activo`:
    SQLite devuelve 0/1 y sin este modelo el mismo concepto viajaba como
    entero en un endpoint y como booleano en otro.
    """

    id: int
    sku_origen: str
    sku_destino: str
    tipo: str
    fuente: str
    score: float
    soporte: int | None = None
    confianza: float | None = None
    lift: float | None = None
    justificacion: str
    justificacion_ia: str | None = None
    estado: str
    peso_manual: float | None = None
    nombre_origen: str
    nombre_destino: str
    stock_destino: int
    activo_destino: bool
