"""Configuracion leida de backend/.env sin dependencias externas.

Se evita python-dotenv y pydantic-settings a proposito: son ocho lineas de parseo
y el proyecto se compromete a no arrastrar dependencias que no aporten.
"""

import os
from pathlib import Path

DIR_BACKEND = Path(__file__).resolve().parent.parent
RAIZ = DIR_BACKEND.parent
DIR_DATOS = RAIZ / "data"
DIR_DOCS = RAIZ / "docs"

CSV_PRODUCTOS = DIR_DATOS / "products.csv"
CSV_VENTAS = DIR_DATOS / "sales.csv"
ARCHIVO_ESQUEMA = Path(__file__).resolve().parent / "schema.sql"


def _cargar_env() -> None:
    archivo = DIR_BACKEND / ".env"
    if not archivo.exists():
        return
    for linea in archivo.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        clave, _, valor = linea.partition("=")
        # Las variables ya presentes en el entorno mandan sobre el archivo.
        os.environ.setdefault(clave.strip(), valor.strip().strip("\"'"))


_cargar_env()


def _ruta_base_datos() -> Path:
    ruta = Path(os.environ.get("DB_PATH", "ferreteria.db"))
    return ruta if ruta.is_absolute() else DIR_BACKEND / ruta


RUTA_BD = _ruta_base_datos()
ORIGENES_CORS = [
    o.strip()
    for o in os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(",")
    if o.strip()
]

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
# Alias que Google mantiene apuntando al flash estable vigente. Fijar una
# version concreta condena el script a romperse: 'gemini-2.0-flash' ya devuelve
# 404 contra la API actual.
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-flash-latest").strip()
