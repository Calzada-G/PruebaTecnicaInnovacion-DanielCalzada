"""Portada y estado. Es lo unico del proyecto que no sirve JSON.

La raiz la abre una persona en el navegador, no un cliente HTTP: un 404 no le
dice si la API arranco bien, y una pagina si. /api/salud es lo mismo para una
maquina -un monitor, un contenedor, un despliegue-.
"""

import sqlite3
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse

from ..db import obtener_bd
from ..schemas.estado import Salud
from ..services import estado_service

router = APIRouter(tags=["estado"])

Conexion = Annotated[sqlite3.Connection, Depends(obtener_bd)]

PORTADA = """<!doctype html>
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


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
def portada(bd: Conexion) -> HTMLResponse:
    datos = estado_service.estado(bd)
    listo = datos["estado"] == "listo"
    contenido = datos["contenido"] or {}
    filas = {
        "Base": datos["base_de_datos"],
        "Productos": contenido.get("productos_activos", "-"),
        "Sucursales": contenido.get("tiendas", "-"),
        "Tickets": contenido.get("tickets", "-"),
        "Relaciones": contenido.get("relaciones", "-"),
    }
    return HTMLResponse(
        PORTADA.format(
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
            frontend=(datos["origenes_cors"] or ["http://localhost:3000"])[0],
        )
    )


@router.get("/api/salud", response_model=Salud, summary="Estado de la API")
def salud(bd: Conexion) -> dict:
    """Si la API arrancó bien, con qué base y qué hay dentro.

    Es la única ruta que el frontend no consume: existe para el operador. Es lo
    que responde «¿está viva y sembrada?» sin tener que abrir la interfaz, y lo
    que consultaría un monitor o el *healthcheck* de un contenedor.

    `estado` vale `listo`, `base vacia` (falta correr el seed) o
    `sin base de datos` (el archivo no existe o no tiene tablas).
    """
    return estado_service.estado(bd)
