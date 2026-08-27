"""Materializa en `relaciones` lo que encuentra cada fuente.

    python scripts/construir_relaciones.py

Es idempotente y conserva los ajustes manuales: se puede volver a correr tras
cada tanda de ventas sin deshacer lo que el negocio bloqueo o fijo.

Por que se materializa:
- El historico solo cambia cuando cambian las ventas, asi que recalcularlo en
  cada peticion seria trabajo tirado.
- Los atributos si se resuelven en cada peticion, porque el sustituto correcto
  depende del perfil de la tienda. Aqui se guardan sin dimension de plaza, como
  relaciones de familia, para que el negocio pueda verlas y ajustarlas: el
  ajuste se aplica igual a la version que se calcula en vivo.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import conectar  # noqa: E402
from app.recomendador.atributos import FAMILIAS, AtributosStrategy  # noqa: E402
from app.recomendador.historico import calcular_reglas  # noqa: E402
from app.repositories import relaciones_repo  # noqa: E402


def relaciones_por_atributos(bd) -> list[dict]:
    estrategia = AtributosStrategy(bd)
    salida: list[dict] = []

    for sku in estrategia._productos:
        for candidato in estrategia._complementos(sku):
            salida.append(
                {
                    "sku_origen": sku,
                    "sku_destino": candidato.sku,
                    "tipo": "complemento",
                    "fuente": "atributos",
                    "score": round(candidato.score, 4),
                    "soporte": None,
                    "confianza": None,
                    "lift": None,
                    "justificacion": candidato.justificacion,
                }
            )

    # Los sustitutos se guardan como pares de familia, sin plaza: cual conviene
    # depende del perfil y eso se decide al servir, no al construir.
    for nombre_familia, miembros in FAMILIAS.items():
        for origen in miembros:
            for destino in miembros:
                if origen == destino:
                    continue
                salida.append(
                    {
                        "sku_origen": origen,
                        "sku_destino": destino,
                        "tipo": "sustituto",
                        "fuente": "atributos",
                        "score": 0.0,
                        "soporte": None,
                        "confianza": None,
                        "lift": None,
                        "justificacion": (
                            f"Misma familia funcional ({nombre_familia}); "
                            f"cual conviene depende del perfil de la plaza."
                        ),
                    }
                )
    return salida


def construir() -> dict[str, int]:
    bd = conectar()
    try:
        historico = calcular_reglas(bd)
        atributos = relaciones_por_atributos(bd)

        # UNIQUE es (origen, destino, tipo), asi que un par que ambas fuentes
        # proponen ocupa una sola fila. Gana el historico porque lleva soporte,
        # confianza y lift; la regla por atributos sigue actuando al servir.
        combinadas: dict[tuple[str, str, str], dict] = {}
        for relacion in atributos + historico:
            clave = (
                relacion["sku_origen"],
                relacion["sku_destino"],
                relacion["tipo"],
            )
            combinadas[clave] = relacion

        cur = bd.cursor()
        cur.execute("BEGIN IMMEDIATE")
        relaciones_repo.reemplazar(bd, list(combinadas.values()))
        borradas = relaciones_repo.eliminar_huerfanas(bd, list(combinadas))
        bd.commit()

        return {
            "historico": len(historico),
            "atributos": len(atributos),
            "total": len(combinadas),
            "borradas": borradas,
        }
    except Exception:
        bd.rollback()
        raise
    finally:
        bd.close()


if __name__ == "__main__":
    resumen = construir()
    print(
        f"Relaciones construidas: {resumen['total']}\n"
        f"  historico: {resumen['historico']} reglas de co-ocurrencia\n"
        f"  atributos: {resumen['atributos']} relaciones de dominio\n"
        f"  huerfanas eliminadas: {resumen['borradas']}"
    )
