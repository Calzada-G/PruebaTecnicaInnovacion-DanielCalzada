"""Punto de entrada de la API.

Todos los endpoints se declaran con `def` sincrono, nunca `async def`: sqlite3
es bloqueante y con `async def` bloquearia el event loop, con lo que el test de
concurrencia dejaria de medir lo que dice medir. Con `def`, FastAPI los ejecuta
en su threadpool.
"""

import sqlite3

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import ORIGENES_CORS
from .db import obtener_bd

app = FastAPI(
    title="Ferreteria - inventario y recomendaciones",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGENES_CORS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/tiendas")
def listar_tiendas(bd: sqlite3.Connection = Depends(obtener_bd)) -> list[dict]:
    filas = bd.execute(
        "SELECT id, nombre, perfil, acento FROM tiendas ORDER BY nombre"
    ).fetchall()
    return [dict(f) for f in filas]
