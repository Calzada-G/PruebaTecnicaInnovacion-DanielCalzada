"""Punto de entrada de la API.

Todos los endpoints se declaran con `def` sincrono, nunca `async def`: sqlite3
es bloqueante y con `async def` bloquearia el event loop, con lo que el test de
concurrencia dejaria de medir lo que dice medir. Con `def`, FastAPI los ejecuta
en su threadpool.
"""

import sqlite3

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import ORIGENES_CORS
from .db import obtener_bd
from .errores import (
    ErrorDominio,
    ProductoDuplicado,
    ProductoNoEncontrado,
    StockInsuficiente,
    TiendaNoEncontrada,
)
from .routers import compras, productos

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

# Traducir excepciones de dominio a HTTP aqui, y no en cada router, es lo que
# permite que los servicios no importen nada de FastAPI.
_ESTADOS = {
    ProductoNoEncontrado: 404,
    TiendaNoEncontrada: 404,
    ProductoDuplicado: 409,
    StockInsuficiente: 409,
}


@app.exception_handler(ErrorDominio)
def manejar_error_dominio(_: Request, exc: ErrorDominio) -> JSONResponse:
    estado = next(
        (codigo for clase, codigo in _ESTADOS.items() if isinstance(exc, clase)), 400
    )
    detalle: dict[str, object] = {"detail": str(exc)}
    if isinstance(exc, StockInsuficiente):
        # El mostrador necesita el numero para el mensaje "Quedan 3", no solo el texto.
        detalle |= {"sku": exc.sku, "disponible": exc.disponible}
    return JSONResponse(status_code=estado, content=detalle)


app.include_router(productos.router)
app.include_router(compras.router)


@app.get("/api/tiendas")
def listar_tiendas(bd: sqlite3.Connection = Depends(obtener_bd)) -> list[dict]:
    filas = bd.execute(
        "SELECT id, nombre, perfil, acento FROM tiendas ORDER BY nombre"
    ).fetchall()
    return [dict(f) for f in filas]
