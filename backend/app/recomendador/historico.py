"""Reglas de asociacion desde el historial de tickets.

Con 42 tickets y 45 pares co-ocurrentes de los que solo 8 aparecen mas de una
vez, el lift sobre n=2 es ruido estadistico. Por eso esta fuente es evidencia
auditable, NO el motor: el score no es la confianza cruda sino su limite
inferior de Wilson, que castiga automaticamente lo visto una sola vez.

El historico solo produce complementos. Los sustitutos son, por definicion,
productos que NO se compran juntos: nadie se lleva el tornillo de carbon y el
de inoxidable para el mismo trabajo. Esa imposibilidad estructural es la razon
de que exista la capa de atributos.
"""

import math
import sqlite3
from itertools import permutations

from .base import Candidato


def limite_inferior_wilson(exitos: int, intentos: int, z: float = 1.96) -> float:
    """Extremo inferior del intervalo de Wilson para una proporcion.

    Una regla vista 1 de 3 veces y otra vista 2 de 3 tienen confianzas 0.33 y
    0.67, pero sus limites inferiores se separan mucho mas: es la forma honesta
    de ordenar evidencia escasa sin inventar significancia que no hay.
    """
    if intentos <= 0:
        return 0.0
    p = exitos / intentos
    z2 = z * z
    denominador = 1 + z2 / intentos
    centro = (p + z2 / (2 * intentos)) / denominador
    margen = (
        z
        * math.sqrt(p * (1 - p) / intentos + z2 / (4 * intentos * intentos))
        / denominador
    )
    return max(0.0, centro - margen)


def calcular_reglas(bd: sqlite3.Connection) -> list[dict]:
    """Co-ocurrencia por ticket -> soporte, confianza, lift y score normalizado."""
    filas = bd.execute("SELECT ticket_id, sku FROM ventas").fetchall()
    canastas: dict[str, set[str]] = {}
    for fila in filas:
        canastas.setdefault(fila["ticket_id"], set()).add(fila["sku"])

    total_tickets = len(canastas)
    if total_tickets == 0:
        return []

    tickets_por_sku: dict[str, int] = {}
    tickets_por_par: dict[tuple[str, str], int] = {}
    for skus in canastas.values():
        for sku in skus:
            tickets_por_sku[sku] = tickets_por_sku.get(sku, 0) + 1
        for origen, destino in permutations(sorted(skus), 2):
            tickets_por_par[(origen, destino)] = (
                tickets_por_par.get((origen, destino), 0) + 1
            )

    reglas = []
    for (origen, destino), soporte in tickets_por_par.items():
        soporte_origen = tickets_por_sku[origen]
        confianza = soporte / soporte_origen
        soporte_destino_relativo = tickets_por_sku[destino] / total_tickets
        lift = confianza / soporte_destino_relativo if soporte_destino_relativo else 0.0
        reglas.append(
            {
                "sku_origen": origen,
                "sku_destino": destino,
                "tipo": "complemento",
                "fuente": "historico",
                "soporte": soporte,
                "confianza": round(confianza, 4),
                "lift": round(lift, 4),
                "score": limite_inferior_wilson(soporte, soporte_origen),
                "justificacion": (
                    f"Se llevaron juntos en {soporte} de los {soporte_origen} "
                    f"tickets con este producto."
                ),
            }
        )

    # Normalizacion global de la fuente: la regla mejor sustentada vale 1.0 y
    # el resto queda relativo a ella. Se normaliza sobre todas las anclas, no
    # dentro de cada una, o un par debil seria un 1.0 solo por estar solo.
    maximo = max((r["score"] for r in reglas), default=0.0)
    for regla in reglas:
        regla["score"] = round(regla["score"] / maximo, 4) if maximo else 0.0
    return reglas


class HistoricoStrategy:
    """Lee las reglas ya materializadas en la tabla `relaciones`.

    No recalcula en cada peticion: las reglas cambian cuando se reconstruyen
    con scripts/construir_relaciones.py, y asi el negocio ve y ajusta
    exactamente las mismas filas que consume el mostrador.
    """

    nombre = "historico"

    def __init__(self, bd: sqlite3.Connection):
        self._bd = bd

    def generar(self, sku: str, tienda: str) -> list[Candidato]:
        filas = self._bd.execute(
            """SELECT sku_destino, tipo, score, soporte, confianza, lift,
                      justificacion, justificacion_ia
                 FROM relaciones
                WHERE sku_origen = ? AND fuente = ?""",
            (sku, self.nombre),
        ).fetchall()
        return [
            Candidato(
                sku=f["sku_destino"],
                tipo=f["tipo"],
                score=f["score"],
                fuente=self.nombre,
                justificacion=f["justificacion_ia"] or f["justificacion"],
                soporte=f["soporte"],
                confianza=f["confianza"],
                lift=f["lift"],
            )
            for f in filas
        ]
