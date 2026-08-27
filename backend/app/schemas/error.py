"""Forma de los errores en la documentacion.

`app/errores.py` define las excepciones de dominio; esto describe como se ven
esas excepciones ya convertidas en JSON. Sin esto, /docs solo documenta el 200
y el 422 de Pydantic, y quien integra tiene que descubrir a base de prueba y
error que un 409 de compra trae `disponible`.

RESPUESTAS se reutiliza en cada ruta para no repetir el mismo bloque.
"""

from pydantic import BaseModel


class ErrorRespuesta(BaseModel):
    """Todo error de negocio responde con este cuerpo, como minimo."""

    detail: str

    model_config = {
        "json_schema_extra": {"examples": [{"detail": "No existe el producto SKU999."}]}
    }


class ErrorSinExistencia(ErrorRespuesta):
    """El 409 de compra ademas dice de que SKU y cuanto queda.

    El mostrador necesita el numero para escribir «Quedan 3»; sin el tendria
    que sacarlo del texto con una expresion regular.
    """

    sku: str
    disponible: int | None = None

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "detail": "No hay suficiente inventario de SKU007. Quedan 3.",
                    "sku": "SKU007",
                    "disponible": 3,
                }
            ]
        }
    }


def _respuesta(descripcion: str, modelo: type[BaseModel] = ErrorRespuesta) -> dict:
    return {"description": descripcion, "model": modelo}


RESPUESTAS = {
    "producto_no_encontrado": {404: _respuesta("No existe ese SKU.")},
    "tienda_no_encontrada": {404: _respuesta("No existe esa sucursal.")},
    "relacion_no_encontrada": {404: _respuesta("No existe esa relacion.")},
    "sku_duplicado": {409: _respuesta("Ya hay un producto con ese SKU.")},
    "sin_existencia": {
        409: _respuesta(
            "No hay inventario suficiente para alguna linea; no se descuento nada.",
            ErrorSinExistencia,
        )
    },
}
