"""Siembra la base desde los CSV. Idempotente: borra y recrea en cada ejecucion.

Uso:  python -m app.seed
"""

import csv
import sqlite3
import sys
import unicodedata
from pathlib import Path

from .config import ARCHIVO_ESQUEMA, CSV_PRODUCTOS, CSV_VENTAS, RUTA_BD
from .db import conectar

# Las 5 tiendas del enunciado. `perfil` es lo que consume el recomendador.
#
# Cancun, Chihuahua, CDMX y Monterrey tienen su perfil respaldado por el
# historico de ventas. MERIDA NO APARECE EN sales.csv: su perfil costero salino
# esta asignado por conocimiento externo del negocio (peninsula de Yucatan,
# clima marino), no derivado de datos. Es un supuesto declarado, no un hallazgo.
TIENDAS = [
    ("cdmx", "CDMX", "interior_urbano", "#6B7280"),
    ("cancun", "Cancún", "costero_salino", "#0E7C86"),
    ("merida", "Mérida", "costero_salino", "#0E7C86"),
    ("chihuahua", "Chihuahua", "sol_directo_seco", "#C87A0A"),
    ("monterrey", "Monterrey", "taller_metalmecanico", "#B4472A"),
]

# Peso inicial de cada fuente en el ranking. El negocio los cambia desde
# /api/config/pesos sin tocar codigo.
#
# El historico pesa mas que los atributos porque una co-compra observada es
# evidencia real; lo que evita que el ruido gane es que historico.py ya castiga
# los pares de soporte 1 antes de llegar aqui, no un peso bajo.
PESOS_INICIALES = [("historico", 1.0), ("atributos", 0.8), ("manual", 1.5)]


def id_tienda(nombre: str) -> str:
    """'Cancún' -> 'cancun'. Evita arrastrar acentos a ids, URLs y joins."""
    sin_acentos = unicodedata.normalize("NFKD", nombre.strip())
    sin_acentos = "".join(c for c in sin_acentos if not unicodedata.combining(c))
    return sin_acentos.lower().replace(" ", "_")


def _borrar_base(ruta: Path) -> None:
    # WAL deja dos archivos satelite; borrar solo el .db dejaria basura que
    # reaparece como datos fantasma en la siguiente conexion.
    for sufijo in ("", "-wal", "-shm"):
        archivo = Path(str(ruta) + sufijo)
        if archivo.exists():
            archivo.unlink()


def sembrar(ruta: Path | None = None) -> dict[str, int]:
    ruta = ruta or RUTA_BD
    _borrar_base(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)

    conexion = conectar(ruta)
    try:
        conexion.executescript(ARCHIVO_ESQUEMA.read_text(encoding="utf-8"))
        cur = conexion.cursor()
        cur.execute("BEGIN IMMEDIATE")

        cur.executemany(
            "INSERT INTO tiendas (id, nombre, perfil, acento) VALUES (?, ?, ?, ?)",
            TIENDAS,
        )
        cur.executemany(
            "INSERT INTO config_pesos (fuente, peso) VALUES (?, ?)", PESOS_INICIALES
        )

        with CSV_PRODUCTOS.open(encoding="utf-8-sig", newline="") as f:
            productos = [
                (
                    fila["sku"].strip(),
                    fila["nombre"].strip(),
                    fila["descripcion"].strip(),
                    fila["categoria"].strip(),
                    fila["material"].strip(),
                    fila["uso_recomendado"].strip(),
                    float(fila["precio"]),
                    int(fila["stock"]),
                )
                for fila in csv.DictReader(f)
                if fila.get("sku")
            ]
        cur.executemany(
            """INSERT INTO productos
               (sku, nombre, descripcion, categoria, material, uso_recomendado,
                precio, stock)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            productos,
        )

        conocidas = {t[0] for t in TIENDAS}
        with CSV_VENTAS.open(encoding="utf-8-sig", newline="") as f:
            ventas = []
            for fila in csv.DictReader(f):
                if not fila.get("ticket_id"):
                    continue
                tienda = id_tienda(fila["tienda"])
                if tienda not in conocidas:
                    raise ValueError(
                        f"sales.csv trae la tienda '{fila['tienda']}' "
                        f"(id '{tienda}') que no esta en TIENDAS."
                    )
                ventas.append(
                    (
                        fila["ticket_id"].strip(),
                        fila["sku"].strip(),
                        int(fila["cantidad"]),
                        tienda,
                        fila["fecha"].strip(),
                    )
                )
        cur.executemany(
            """INSERT INTO ventas (ticket_id, sku, cantidad, tienda_id, fecha)
               VALUES (?, ?, ?, ?, ?)""",
            ventas,
        )

        conexion.commit()

        tickets = cur.execute(
            "SELECT COUNT(DISTINCT ticket_id) FROM ventas"
        ).fetchone()[0]
        return {
            "productos": len(productos),
            "ventas": len(ventas),
            "tickets": tickets,
            "tiendas": len(TIENDAS),
        }
    except Exception:
        conexion.rollback()
        raise
    finally:
        conexion.close()


if __name__ == "__main__":
    try:
        resumen = sembrar()
    except (OSError, ValueError, sqlite3.Error) as exc:
        print(f"Fallo la siembra: {exc}", file=sys.stderr)
        raise SystemExit(1)
    print(f"Base creada en {RUTA_BD}")
    print(
        f"  {resumen['productos']} productos"
        f"  |  {resumen['ventas']} lineas de venta"
        f" en {resumen['tickets']} tickets"
        f"  |  {resumen['tiendas']} tiendas"
    )
