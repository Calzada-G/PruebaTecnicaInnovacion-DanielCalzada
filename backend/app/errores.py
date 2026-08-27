"""Excepciones de dominio.

Los servicios las lanzan sin saber nada de HTTP; los routers las traducen a
codigos de estado. Asi la logica de negocio es testeable sin levantar FastAPI.
"""


class ErrorDominio(Exception):
    pass


class ProductoNoEncontrado(ErrorDominio):
    def __init__(self, sku: str):
        self.sku = sku
        super().__init__(f"No existe el producto {sku}.")


class ProductoDuplicado(ErrorDominio):
    def __init__(self, sku: str):
        self.sku = sku
        super().__init__(f"Ya existe un producto con SKU {sku}.")


class StockInsuficiente(ErrorDominio):
    """El UPDATE condicional no afecto ninguna fila.

    Cubre tres casos que desde SQL son indistinguibles y que desde negocio
    significan lo mismo: no se puede vender. `disponible` se consulta despues,
    solo para el mensaje al vendedor.
    """

    def __init__(self, sku: str, solicitado: int, disponible: int | None = None):
        self.sku = sku
        self.solicitado = solicitado
        self.disponible = disponible
        if disponible is None:
            super().__init__(f"No hay suficiente inventario de {sku}.")
        else:
            super().__init__(
                f"No hay suficiente inventario de {sku}. Quedan {disponible}."
            )


class TiendaNoEncontrada(ErrorDominio):
    def __init__(self, tienda: str):
        self.tienda = tienda
        super().__init__(f"No existe la tienda {tienda}.")


class CompraInvalida(ErrorDominio):
    pass


class RelacionNoEncontrada(ErrorDominio):
    def __init__(self, id_relacion: int):
        self.id_relacion = id_relacion
        super().__init__(f"No existe la relacion {id_relacion}.")
