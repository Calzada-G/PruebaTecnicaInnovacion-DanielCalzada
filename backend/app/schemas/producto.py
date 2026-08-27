"""Contrato de entrada y salida de productos, con sus limites.

Los limites se declaran UNA vez como tipos reutilizables y se usan igual en el
alta y en la edicion. Duplicarlos en los dos modelos era la via segura para que
un dia divergieran y el PATCH aceptara lo que el POST rechaza.
"""

from typing import Annotated

from pydantic import AfterValidator, BaseModel, Field, StringConstraints


def _sin_control(texto: str) -> str:
    """Rechaza caracteres de control: tabuladores, saltos y bytes invisibles.

    Llegan casi siempre al pegar desde Excel o un PDF. No rompen la base
    (las consultas son parametrizadas) pero descuadran tablas y hacen que dos
    productos identicos parezcan distintos.
    """
    if any(c.isprintable() is False for c in texto):
        raise ValueError("no puede contener caracteres invisibles o saltos de linea")
    return " ".join(texto.split())


Texto = Annotated[str, AfterValidator(_sin_control)]

# El SKU viaja en la URL (/api/productos/{sku}), asi que no puede llevar
# espacios, acentos ni barras. Se normaliza a mayusculas para que 'sku001' y
# 'SKU001' no acaben siendo dos productos distintos.
Sku = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        to_upper=True,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{1,23}$",
    ),
]

Nombre = Annotated[Texto, StringConstraints(strip_whitespace=True, min_length=2, max_length=120)]
Categoria = Annotated[Texto, StringConstraints(strip_whitespace=True, min_length=2, max_length=40)]
Material = Annotated[Texto, StringConstraints(strip_whitespace=True, max_length=60)]
Uso = Annotated[Texto, StringConstraints(strip_whitespace=True, max_length=80)]
Descripcion = Annotated[Texto, StringConstraints(strip_whitespace=True, max_length=300)]

# Topes altos pero finitos: sin ellos cabe un precio de 1e308, que rompe
# cualquier suma posterior, y un stock que ningun almacen puede sostener.
Precio = Annotated[float, Field(ge=0, le=9_999_999)]
Existencia = Annotated[int, Field(ge=0, le=1_000_000)]


class ProductoCrear(BaseModel):
    sku: Sku
    nombre: Nombre
    categoria: Categoria
    precio: Precio
    stock: Existencia
    descripcion: Descripcion = ""
    material: Material = ""
    uso_recomendado: Uso = ""


class ProductoActualizar(BaseModel):
    """PATCH: solo se tocan los campos presentes en el cuerpo.

    Los servicios distinguen ausente de nulo con model_dump(exclude_unset=True),
    asi que poner un valor a su default no cuenta como cambio accidental. El SKU
    no esta: es la clave y no se renombra.
    """

    nombre: Nombre | None = None
    categoria: Categoria | None = None
    precio: Precio | None = None
    stock: Existencia | None = None
    descripcion: Descripcion | None = None
    material: Material | None = None
    uso_recomendado: Uso | None = None
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
