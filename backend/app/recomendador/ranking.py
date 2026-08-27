"""Mezcla las fuentes y aplica las reglas de negocio.

Este es el unico punto donde se filtra por existencia. Que sea uno solo es
deliberado: el requisito de no recomendar nunca un producto agotado se cumple
o se rompe aqui, y asi hay un solo sitio que auditar y que testear.
"""

from .base import Candidato, FuenteRecomendacion

# Una relacion fijada por el negocio manda sobre cualquier score calculado.
BONO_FIJADA = 10.0


def _puntuar(
    candidato: Candidato, pesos: dict[str, float], ajuste: dict | None
) -> float:
    if ajuste and ajuste.get("peso_manual") is not None:
        # Peso manual es un override absoluto, no un multiplicador: el negocio
        # dice cuanto vale la relacion, no cuanto la corrige.
        base = float(ajuste["peso_manual"])
    else:
        base = candidato.score * pesos.get(candidato.fuente, 1.0)
    if ajuste and ajuste.get("estado") == "fijada":
        base += BONO_FIJADA
    return base


def mezclar(
    fuentes: list[FuenteRecomendacion],
    sku: str,
    tienda: str,
    pesos: dict[str, float],
    ajustes: dict[tuple[str, str, str], dict],
    comprables: set[str],
    excluir: set[str],
    # Seis y no tres o cuatro: los consumibles de una actividad puntuan casi
    # igual entre si y con un tope corto llenan la lista con casi-duplicados
    # (dos varillas de soldar) dejando fuera el accesorio y el EPP, que es
    # justo lo que el vendedor no tiene presente.
    limite: int = 6,
) -> dict:
    mejores: dict[tuple[str, str], tuple[float, Candidato]] = {}

    for fuente in fuentes:
        for candidato in fuente.generar(sku, tienda):
            # Filtros duros. No son ponderaciones: lo que no pasa de aqui no
            # existe, por muy alto que puntue.
            if candidato.sku == sku or candidato.sku in excluir:
                continue
            if candidato.sku not in comprables:
                continue

            ajuste = ajustes.get((sku, candidato.sku, candidato.tipo))
            if ajuste and ajuste.get("estado") == "bloqueada":
                continue

            puntaje = _puntuar(candidato, pesos, ajuste)
            clave = (candidato.sku, candidato.tipo)
            anterior = mejores.get(clave)
            if anterior is None:
                mejores[clave] = (puntaje, candidato)
                continue

            # Que dos fuentes propongan el mismo par es corroboracion, no
            # empate: se queda el puntaje mayor, pero para mostrar gana el
            # candidato con tickets detras. Al cliente lo convence "se llevaron
            # juntos en 2 de 3 tickets", no "por atributos".
            if candidato.soporte is not None and anterior[1].soporte is None:
                visible = candidato
            elif anterior[1].soporte is not None and candidato.soporte is None:
                visible = anterior[1]
            else:
                visible = candidato if puntaje > anterior[0] else anterior[1]
            mejores[clave] = (max(anterior[0], puntaje), visible)

    def serializar(candidato: Candidato, puntaje: float) -> dict:
        return {
            "sku": candidato.sku,
            "tipo": candidato.tipo,
            "score": round(puntaje, 4),
            "fuente": candidato.fuente,
            "justificacion": candidato.justificacion,
            "soporte": candidato.soporte,
            "confianza": candidato.confianza,
            "lift": candidato.lift,
        }

    sustitutos = sorted(
        ((p, c) for (_, tipo), (p, c) in mejores.items() if tipo == "sustituto"),
        key=lambda par: (-par[0], par[1].sku),
    )
    complementos = sorted(
        ((p, c) for (_, tipo), (p, c) in mejores.items() if tipo == "complemento"),
        key=lambda par: (-par[0], par[1].sku),
    )

    sustituto = serializar(sustitutos[0][1], sustitutos[0][0]) if sustitutos else None
    sku_sustituto = sustituto["sku"] if sustituto else None

    return {
        "sustituto": sustituto,
        "complementos": [
            serializar(c, p)
            for p, c in complementos
            if c.sku != sku_sustituto
        ][:limite],
    }
