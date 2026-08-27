"""Mezcla las fuentes y aplica las reglas de negocio.

Este es el unico punto donde se filtra por existencia. Que sea uno solo es
deliberado: el requisito de no recomendar nunca un producto agotado se cumple
o se rompe aqui, y asi hay un solo sitio que auditar y que testear.
"""

from collections.abc import Callable

from .base import Candidato, FuenteRecomendacion

# Una relacion fijada por el negocio manda sobre cualquier score calculado.
BONO_FIJADA = 10.0


def exigencia(pesos: dict[str, float]) -> float:
    """Que tan cerca del mejor candidato hay que estar para seguir saliendo.

    SIN ESTO LOS PESOS NO CAMBIABAN NADA. Medido: con los tres modos del panel,
    de 140 consultas (28 productos x 5 plazas) cambiaba el orden en 45, 60 y 20
    casos, y el CONJUNTO de sugerencias en cero. La razon es que un peso solo
    multiplica el puntaje, y como casi ningun producto tiene mas de seis
    candidatos, el tope nunca recorta: nadie entra ni sale, solo se reordenan.

    Un peso por fuente responde "cual prefiero", pero el negocio esta
    preguntando otra cosa: "cuanta evidencia exijo para ofrecer algo". Eso es un
    corte, no un multiplicador.

    Se deriva de los pesos ya existentes en vez de guardarse aparte, para que
    siga habiendo un solo sitio que configurar:

        atributos muy por debajo de historico  -> exigente  (solo lo comprobado)
        atributos a la par o por encima        -> permisivo (descubrir mas)

    El corte es RELATIVO al mejor candidato de cada consulta, nunca absoluto:
    asi una plaza sin historico -Merida- se queda con sus sugerencias por
    atributos en vez de quedarse en blanco, que es lo que pasaria con un umbral
    fijo. Lo que cambia ahi es cuantas acompanan a la mejor, no que desaparezca.
    """
    historico = pesos.get("historico", 1.0)
    atributos = pesos.get("atributos", 1.0)
    if historico <= 0 or atributos >= historico:
        return 0.0
    return 1 - atributos / historico


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
    misma_familia: Callable[[str, str], bool] | None = None,
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

            # Dos productos de la misma familia son alternativas, nunca se
            # llevan juntos. El historico si puede proponerlo (alguien compro
            # tornillo de carbon y galvanizado en el mismo ticket), y hacerle
            # caso daria un consejo contradictorio: "cambialo por el inox" y
            # "llevate tambien el galvanizado" a la vez. La regla se aplica
            # aqui, sobre todas las fuentes, y no dentro de una sola.
            if (
                candidato.tipo == "complemento"
                and misma_familia
                and misma_familia(sku, candidato.sku)
            ):
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

    restantes = [(p, c) for p, c in complementos if c.sku != sku_sustituto]

    # El corte es lo que hace que cambiar de modo cambie QUE se ofrece y no
    # solo en que orden. Relativo al mejor de esta consulta, asi que el primero
    # siempre pasa: exigir mas evidencia acorta la lista, nunca la vacia.
    if restantes:
        minimo = restantes[0][0] * exigencia(pesos)
        restantes = [(p, c) for p, c in restantes if p >= minimo]

    return {
        "sustituto": sustituto,
        "complementos": [serializar(c, p) for p, c in restantes][:limite],
    }
