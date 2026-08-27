from pydantic import BaseModel, ConfigDict, Field


class ProductoCrear(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    sku: str = Field(min_length=1, max_length=32)
    nombre: str = Field(min_length=1, max_length=200)
    descripcion: str = ""
    categoria: str = Field(min_length=1, max_length=80)
    material: str = ""
    uso_recomendado: str = ""
    precio: float = Field(ge=0)
    stock: int = Field(ge=0)


class ProductoActualizar(BaseModel):
    """PATCH: solo se tocan los campos presentes en el cuerpo.

    Los servicios distinguen ausente de nulo con model_dump(exclude_unset=True),
    asi que poner un valor a su default no cuenta como cambio accidental.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    nombre: str | None = Field(default=None, min_length=1, max_length=200)
    descripcion: str | None = None
    categoria: str | None = Field(default=None, min_length=1, max_length=80)
    material: str | None = None
    uso_recomendado: str | None = None
    precio: float | None = Field(default=None, ge=0)
    stock: int | None = Field(default=None, ge=0)
    activo: bool | None = None


class Producto(BaseModel):
    sku: str
    nombre: str
    descripcion: str
    categoria: str
    material: str
    uso_recomendado: str
    precio: float
    stock: int
    activo: bool
