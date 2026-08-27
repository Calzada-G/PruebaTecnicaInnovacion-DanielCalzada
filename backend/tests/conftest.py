"""Cada test corre contra una base sembrada desde cero en un directorio temporal.

Se usa una base en disco y no `:memory:` a proposito: el test de concurrencia
necesita varias conexiones reales compartiendo el mismo archivo, que es lo que
ejercita WAL, BEGIN IMMEDIATE y busy_timeout.
"""

import sys
import warnings
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

warnings.filterwarnings("ignore", category=DeprecationWarning)

from app import db as modulo_db  # noqa: E402
from app.seed import sembrar  # noqa: E402


@pytest.fixture()
def ruta_bd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    ruta = tmp_path / "prueba.db"
    sembrar(ruta)
    # conectar() lee RUTA_BD por defecto; apuntarla a la base temporal hace que
    # tanto la dependencia de FastAPI como los hilos del test usen este archivo.
    monkeypatch.setattr(modulo_db, "RUTA_BD", ruta)
    return ruta


@pytest.fixture()
def bd(ruta_bd: Path):
    conexion = modulo_db.conectar(ruta_bd)
    yield conexion
    conexion.close()


@pytest.fixture()
def con_relaciones(bd):
    """Base sembrada y con la tabla `relaciones` ya construida.

    Equivale a haber corrido scripts/construir_relaciones.py. Varios tests lo
    necesitaban y cada uno repetia el mismo bloque de seis lineas.
    """
    from app.recomendador.historico import calcular_reglas
    from app.repositories import relaciones_repo
    from scripts.construir_relaciones import relaciones_por_atributos

    combinadas = {}
    for regla in relaciones_por_atributos(bd) + calcular_reglas(bd):
        combinadas[(regla["sku_origen"], regla["sku_destino"], regla["tipo"])] = regla
    bd.execute("BEGIN IMMEDIATE")
    relaciones_repo.reemplazar(bd, list(combinadas.values()))
    bd.commit()
    return bd


@pytest.fixture()
def cliente(ruta_bd: Path):
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as c:
        yield c
