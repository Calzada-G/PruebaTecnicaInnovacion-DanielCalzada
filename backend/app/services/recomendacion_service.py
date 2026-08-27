"""Orquesta las fuentes de recomendacion para un producto y una tienda."""

import sqlite3

from ..errores import ProductoNoEncontrado, TiendaNoEncontrada
from ..recomendador.atributos import AtributosStrategy
from ..recomendador.historico import HistoricoStrategy
from ..recomendador.ranking import mezclar
from ..repositories import productos_repo, relaciones_repo, ventas_repo


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
    if not ventas_repo.existe_tienda(bd, tienda):
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
    )
