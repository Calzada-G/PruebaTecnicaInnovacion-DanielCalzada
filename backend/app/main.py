"""Punto de entrada de la API: montaje, CORS y traduccion de errores.

Todos los endpoints se declaran con `def` sincrono, nunca `async def`: sqlite3
es bloqueante y con `async def` bloquearia el event loop, con lo que el test de
concurrencia dejaria de medir lo que dice medir. Con `def`, FastAPI los ejecuta
en su threadpool.
"""

import sqlite3
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import ORIGENES_CORS, VERSION
from .db import conectar
from .errores import (
    ErrorDominio,
    IANoDisponible,
    ProductoDuplicado,
    ProductoNoEncontrado,
    RelacionNoEncontrada,
    StockInsuficiente,
    TiendaNoEncontrada,
)
from .routers import (
    analisis,
    compras,
    diagnostico,
    estado,
    productos,
    recomendaciones,
    relaciones,
    tiendas,
)
from .services import estado_service

DESCRIPCION = """
Inventario compartido por cinco sucursales y recomendaciones por plaza.

**Dos garantias que sostienen todo lo demas:**

* El inventario **nunca queda negativo**, ni con cobros simultaneos desde dos
  plazas. La comprobacion vive dentro del `UPDATE ... WHERE stock >= ?`, no en
  un `SELECT` previo.
* **Nunca se recomienda lo que no se puede vender**: agotado, dado de baja,
  bloqueado por el negocio o ya presente en el ticket queda fuera por filtro
  duro, no por puntaje bajo.

`tienda` aparece en casi todas las rutas y **no filtra el inventario**, que es
el mismo en las cinco: cambia el orden del catalogo y cambia que se recomienda.
"""


@asynccontextmanager
async def ciclo_de_vida(_: FastAPI):
    """Deja en la consola de uvicorn la prueba de que la API quedo operativa.

    Sin esto, arrancar solo imprime 'Application startup complete', que no dice
    si encontro la base ni desde que origen aceptara al frontend. Es la primera
    pregunta de cualquiera que clona el repositorio.
    """
    try:
        conexion = conectar()
        try:
            datos = estado_service.estado(conexion)
        finally:
            conexion.close()
    except sqlite3.Error as error:  # pragma: no cover - la base no se pudo abrir
        print(f"\n  Ferreteria Salinas - API {VERSION}")
        print(f"  No se pudo abrir la base: {error}\n", flush=True)
        yield
        return

    lineas = [f"\n  Ferreteria Salinas - API {datos['version']}"]
    lineas.append(f"  Base de datos : {datos['base_de_datos']}")
    if datos["contenido"]:
        cuenta = datos["contenido"]
        lineas.append(
            f"  Contenido     : {cuenta['productos_activos']} productos activos - "
            f"{cuenta['tiendas']} sucursales - {cuenta['tickets']} tickets - "
            f"{cuenta['relaciones']} relaciones "
            f"({cuenta['relaciones_redactadas_por_ia']} redactadas por IA)"
        )
    if datos["estado"] != "listo":
        lineas.append(f"  ATENCION      : {datos['estado'].upper()}")
        lineas.append("  Falta sembrar : python -m app.seed")
        lineas.append("                  python scripts/construir_relaciones.py")
    lineas.append(f"  Frontend      : {', '.join(datos['origenes_cors'])}")
    lineas.append("  Comprobalo en : http://localhost:8000/  o  /docs\n")
    # flush: si la salida se redirige a un archivo, sin esto el banner aparece
    # cuando se llena el bufer, es decir cuando ya no sirve de nada.
    print("\n".join(lineas), flush=True)
    yield


app = FastAPI(
    title="Ferreteria Salinas - inventario y recomendaciones",
    description=DESCRIPCION,
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
    # 503 y no 500: el sistema esta bien, lo que falta es un servicio
    # externo y opcional.
    IANoDisponible: 503,
}


@app.exception_handler(ErrorDominio)
def manejar_error_dominio(_: Request, exc: ErrorDominio) -> JSONResponse:
    codigo = next(
        (estado for clase, estado in _ESTADOS.items() if isinstance(exc, clase)), 400
    )
    detalle: dict[str, object] = {"detail": str(exc)}
    if isinstance(exc, StockInsuficiente):
        # El mostrador necesita el numero para el mensaje "Quedan 3", no solo el texto.
        detalle |= {"sku": exc.sku, "disponible": exc.disponible}
    return JSONResponse(status_code=codigo, content=detalle)


# El orden es el de /docs: primero lo que se usa vendiendo, despues lo que se
# administra, y al final el estado del propio servicio.
app.include_router(productos.router)
app.include_router(compras.router)
app.include_router(recomendaciones.router)
app.include_router(relaciones.router)
app.include_router(diagnostico.router)
app.include_router(analisis.router)
app.include_router(tiendas.router)
app.include_router(estado.router)
