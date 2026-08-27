"""Orquesta las fuentes de recomendacion para un producto y una tienda."""

import sqlite3

from ..errores import ProductoNoEncontrado, TiendaNoEncontrada
from ..recomendador.atributos import AtributosStrategy, familia
from ..recomendador.historico import HistoricoStrategy
from ..recomendador.ranking import mezclar
from ..repositories import productos_repo, relaciones_repo, tiendas_repo


def _comprables(bd: sqlite3.Connection) -> set[str]:
    """Lo unico que se puede recomendar: existe, esta activo y hay unidades."""
    return {
        f["sku"]
        for f in bd.execute(
            "SELECT sku FROM productos WHERE activo = 1 AND stock > 0"
        )
    }


def recomendar(
    bd: sqlite3.Connection,
    sku: str,
    tienda: str,
    excluir: set[str] | None = None,
    limite: int = 6,
) -> dict:
    if productos_repo.obtener(bd, sku) is None:
        raise ProductoNoEncontrado(sku)
    if tiendas_repo.obtener(bd, tienda) is None:
        raise TiendaNoEncontrada(tienda)

    return mezclar(
        fuentes=[HistoricoStrategy(bd), AtributosStrategy(bd)],
        sku=sku,
        tienda=tienda,
        pesos=relaciones_repo.pesos(bd),
        ajustes=relaciones_repo.ajustes(bd),
        comprables=_comprables(bd),
        excluir=excluir or set(),
        limite=limite,
        # El servicio inyecta el conocimiento de familias: asi ranking.py sigue
        # sin depender de ninguna fuente concreta.
        misma_familia=lambda a, b: familia(a) is not None and familia(a) == familia(b),
    )
