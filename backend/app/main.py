"""Punto de entrada de la API.

Todos los endpoints se declaran con `def` sincrono, nunca `async def`: sqlite3
es bloqueante y con `async def` bloquearia el event loop, con lo que el test de
concurrencia dejaria de medir lo que dice medir. Con `def`, FastAPI los ejecuta
en su threadpool.
"""

import sqlite3
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse

from . import db as modulo_db
from .config import ORIGENES_CORS
from .db import conectar, obtener_bd
from .errores import (
    ErrorDominio,
    ProductoDuplicado,
    ProductoNoEncontrado,
    RelacionNoEncontrada,
    StockInsuficiente,
    TiendaNoEncontrada,
)
from .repositories import tiendas_repo
from .routers import compras, diagnostico, productos, recomendaciones, relaciones

VERSION = "0.1.0"


def _resumen(bd: sqlite3.Connection) -> dict:
    """Que hay dentro de la base, para el arranque, la portada y /api/salud.

    Una sola consulta para los tres: si el banner dijera 28 productos y la
    portada otra cosa, el dato dejaria de servir para diagnosticar nada.
    """
    fila = bd.execute(
        """SELECT (SELECT COUNT(*) FROM tiendas)                       AS tiendas,
                  (SELECT COUNT(*) FROM productos WHERE activo = 1)    AS productos,
                  (SELECT COUNT(DISTINCT ticket_id) FROM ventas)       AS tickets,
                  (SELECT COUNT(*) FROM relaciones)                    AS relaciones,
                  (SELECT COUNT(*) FROM relaciones
                    WHERE justificacion_ia IS NOT NULL)                AS redactadas"""
    ).fetchone()
    return dict(fila)


def _estado() -> dict:
    """Resumen tolerante a fallos: la portada tiene que responder igual.

    Si la base no existe todavia, sqlite3 crea el archivo vacio y las consultas
    fallan por tabla inexistente. Ese es justamente el caso que hay que contar
    -falta sembrar-, no un error que tumbe el arranque.
    """
    datos = {
        "estado": "listo",
        "version": VERSION,
        "base_de_datos": str(modulo_db.RUTA_BD),
        "origenes_cors": ORIGENES_CORS,
    }
    try:
        conexion = conectar()
        try:
            datos |= _resumen(conexion)
        finally:
            conexion.close()
    except sqlite3.Error:
        return datos | {"estado": "sin base de datos"}
    if not datos.get("productos"):
        datos["estado"] = "base vacia"
    return datos


@asynccontextmanager
async def ciclo_de_vida(_: FastAPI):
    """Deja en la consola de uvicorn la prueba de que la API quedo operativa.

    Sin esto, arrancar la API solo imprime 'Application startup complete', que
    no dice si encontro la base ni desde que origen aceptara al frontend. Es la
    primera pregunta que se hace cualquiera que clona el repositorio.
    """
    datos = _estado()
    print("\n  Ferreteria Salinas - API " + datos["version"])
    print(f"  Base de datos : {datos['base_de_datos']}")
    if datos["estado"] == "listo":
        print(
            f"  Contenido     : {datos['productos']} productos activos - "
            f"{datos['tiendas']} sucursales - {datos['tickets']} tickets - "
            f"{datos['relaciones']} relaciones ({datos['redactadas']} redactadas por IA)"
        )
    else:
        print(f"  Contenido     : {datos['estado'].upper()}")
        print("  Falta sembrar : python -m app.seed")
        print("                  python scripts/construir_relaciones.py")
    print(f"  Frontend      : {', '.join(datos['origenes_cors'])}")
    print("  Comprobalo en : http://localhost:8000/  o  /docs\n")
    yield


app = FastAPI(
    title="Ferreteria - inventario y recomendaciones",
    version=VERSION,
    lifespan=ciclo_de_vida,
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
    RelacionNoEncontrada: 404,
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
app.include_router(recomendaciones.router)
app.include_router(relaciones.router)
app.include_router(diagnostico.router)


@app.get("/api/tiendas")
def listar_tiendas(bd: sqlite3.Connection = Depends(obtener_bd)) -> list[dict]:
    return [dict(f) for f in tiendas_repo.listar(bd)]


@app.get("/api/salud")
def salud() -> dict:
    """Estado de la API para una maquina: arranque, base y contenido."""
    return _estado()


# La portada la abre una persona en el navegador, no un cliente HTTP. Un JSON
# de 404 no le dice si la API arranco bien; esta pagina si, y ademas la lleva a
# /docs. Es la unica respuesta HTML del proyecto y no toca ninguna ruta /api.
_PORTADA = """<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Ferreteria Salinas - API</title>
<style>
 :root {{ color-scheme: light }}
 body {{ font: 15px/1.55 ui-sans-serif, system-ui, sans-serif; color: #14171a;
        background: #f4f5f6; margin: 0; padding: 48px 20px }}
 main {{ max-width: 620px; margin: 0 auto; background: #fff; border: 1px solid #e2e5e8;
        border-radius: 6px; padding: 28px 30px }}
 h1 {{ font-size: 19px; margin: 0 0 4px }}
 p {{ margin: 0 0 18px; color: #6b7280 }}
 .estado {{ display: inline-block; border-radius: 999px; padding: 2px 10px;
           font-size: 12px; font-weight: 600; background: {fondo}; color: {tinta} }}
 dl {{ display: grid; grid-template-columns: auto 1fr; gap: 6px 18px; margin: 0 0 22px;
      font-family: ui-monospace, monospace; font-size: 13px }}
 dt {{ color: #6b7280 }}
 dd {{ margin: 0 }}
 a {{ display: inline-block; margin-right: 8px; padding: 7px 13px; border-radius: 6px;
     border: 1px solid #e2e5e8; color: #14171a; text-decoration: none; font-size: 13px }}
 a:hover {{ border-color: #b6bcc4; background: #fafafb }}
 code {{ background: #f4f5f6; padding: 2px 5px; border-radius: 4px; font-size: 12px }}
</style></head><body><main>
 <span class="estado">{estado}</span>
 <h1>Ferreteria Salinas &middot; API {version}</h1>
 <p>{mensaje}</p>
 <dl>{filas}</dl>
 <a href="/docs">Documentacion interactiva</a>
 <a href="/api/salud">Estado en JSON</a>
 <a href="/api/tiendas">Sucursales</a>
 <p style="margin-top:22px;font-size:13px">La interfaz corre aparte, en
 <code>{frontend}</code>.</p>
</main></body></html>"""


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def portada() -> HTMLResponse:
    datos = _estado()
    listo = datos["estado"] == "listo"
    filas = {
        "Base": datos["base_de_datos"],
        "Productos": datos.get("productos", "-"),
        "Sucursales": datos.get("tiendas", "-"),
        "Tickets": datos.get("tickets", "-"),
        "Relaciones": datos.get("relaciones", "-"),
    }
    frontend = datos["origenes_cors"][0] if datos["origenes_cors"] else "http://localhost:3000"
    return HTMLResponse(
        _PORTADA.format(
            estado="EN LINEA" if listo else datos["estado"].upper(),
            fondo="#dcfce7" if listo else "#fef3c7",
            tinta="#15803d" if listo else "#b45309",
            version=datos["version"],
            mensaje=(
                "La API responde y encontro su base de datos."
                if listo
                else "La API responde, pero la base todavia no tiene datos: corre "
                "<code>python -m app.seed</code> y despues "
                "<code>python scripts/construir_relaciones.py</code>."
            ),
            filas="".join(f"<dt>{k}</dt><dd>{v}</dd>" for k, v in filas.items()),
            frontend=frontend,
        )
    )
