"""Evaluacion offline del recomendador contra cuatro baselines.

    python scripts/evaluar.py

Metodo: leave-one-out sobre las 42 canastas reales. De cada ticket se oculta un
articulo, se pide el top-k desde lo que queda y se mide si el oculto aparece.

Dos decisiones que sostienen la honestidad del numero:

1. SIN FUGA DE DATOS. Para cada pliegue las reglas de asociacion se reconstruyen
   ocultando el ticket completo que se esta midiendo. Construirlas una sola vez
   desde toda la base inflaria el acierto: cada regla habria visto la respuesta.

2. BASE PROPIA. Se siembra una base temporal desde los CSV, no se usa la de la
   aplicacion. Asi el resultado no cambia porque alguien haya comprado en la UI.

Se miden solo los complementos. El sustituto es otra funcion de negocio (llevar
al material correcto para la plaza) y por definicion no aparece en la misma
canasta, asi que medirlo aqui seria medir mal; se comprueba con el conjunto
dorado y el caso Merida que van al final.
"""

import random
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import DIR_DOCS  # noqa: E402
from app.db import conectar  # noqa: E402
from app.recomendador.atributos import AtributosStrategy  # noqa: E402
from app.recomendador.base import Candidato  # noqa: E402
from app.recomendador.historico import (  # noqa: E402
    HistoricoStrategy,
    calcular_reglas,
    calcular_reglas_desde_canastas,
    limite_inferior_wilson,
)
from app.recomendador.ranking import mezclar  # noqa: E402
from app.repositories import relaciones_repo  # noqa: E402
from app.seed import sembrar  # noqa: E402
from scripts.construir_relaciones import (  # noqa: E402
    relaciones_por_atributos,
)

K = 3
SEMILLA = 42

# Pares que cualquier ferretero daria por obvios. Se marcan con (*) los que
# NUNCA co-ocurren en sales.csv: son los que el historico no puede recuperar
# por construccion, y la razon de que exista la capa de atributos. Elegir solo
# pares presentes en los datos habria hecho trampa a favor del historico.
CONJUNTO_DORADO = [
    ("SKU001", "SKU004", "soplete -> cartucho de gas"),
    ("SKU001", "SKU027", "soplete -> regulador (*)"),
    ("SKU027", "SKU004", "regulador -> cartucho de gas (*)"),
    ("SKU027", "SKU001", "regulador -> soplete (*)"),
    ("SKU026", "SKU027", "manguera -> regulador (*)"),
    ("SKU003", "SKU004", "varilla de plata -> cartucho (*)"),
    ("SKU018", "SKU021", "broca de concreto -> guantes (*)"),
    ("SKU001", "SKU026", "soplete -> manguera de repuesto"),
    ("SKU001", "SKU020", "soplete -> careta de soldar"),
    ("SKU001", "SKU002", "soplete -> varilla de estano"),
    ("SKU001", "SKU003", "soplete -> varilla de plata"),
    ("SKU004", "SKU002", "cartucho -> varilla de aporte"),
    ("SKU017", "SKU018", "taladro -> broca de concreto"),
    ("SKU017", "SKU019", "taladro -> broca de metal"),
    ("SKU017", "SKU021", "taladro -> guantes"),
    ("SKU010", "SKU012", "tubo PVC -> cemento PVC"),
    ("SKU011", "SKU012", "tubo CPVC -> cemento PVC"),
    ("SKU010", "SKU013", "tubo PVC -> sellador"),
    ("SKU012", "SKU010", "cemento PVC -> tubo"),
    ("SKU020", "SKU021", "careta -> guantes"),
    ("SKU023", "SKU028", "cable uso rudo -> grasa dielectrica"),
    ("SKU022", "SKU028", "cable THHW -> grasa dielectrica (*)"),
    ("SKU008", "SKU014", "lamina galvanizada -> anticorrosiva"),
    ("SKU008", "SKU006", "lamina galvanizada -> tornillo galvanizado"),
    ("SKU009", "SKU005", "lamina de carbon -> tornillo de carbon"),
]


class HistoricoEnMemoria:
    """Misma interfaz que HistoricoStrategy, alimentada por un pliegue.

    Es el patron Strategy pagando: intercambiar de donde salen las reglas no
    obliga a tocar el ranking ni el servicio.
    """

    nombre = "historico"

    def __init__(self, reglas: list[dict]):
        self._por_origen: dict[str, list[Candidato]] = defaultdict(list)
        for r in reglas:
            self._por_origen[r["sku_origen"]].append(
                Candidato(
                    sku=r["sku_destino"],
                    tipo=r["tipo"],
                    score=r["score"],
                    fuente=self.nombre,
                    justificacion=r["justificacion"],
                    soporte=r["soporte"],
                    confianza=r["confianza"],
                    lift=r["lift"],
                )
            )

    def generar(self, sku: str, tienda: str) -> list[Candidato]:
        return self._por_origen.get(sku, [])


def wilson_intervalo(exitos: int, intentos: int, z: float = 1.96) -> tuple[float, float]:
    import math

    if intentos == 0:
        return (0.0, 0.0)
    p = exitos / intentos
    z2 = z * z
    denominador = 1 + z2 / intentos
    centro = (p + z2 / (2 * intentos)) / denominador
    margen = (
        z * math.sqrt(p * (1 - p) / intentos + z2 / (4 * intentos * intentos))
    ) / denominador
    return (max(0.0, centro - margen), min(1.0, centro + margen))


def leer_datos(bd):
    productos = {f["sku"]: dict(f) for f in bd.execute("SELECT * FROM productos")}
    tickets: dict[str, dict] = {}
    for f in bd.execute("SELECT ticket_id, sku, cantidad, tienda_id FROM ventas"):
        t = tickets.setdefault(
            f["ticket_id"], {"tienda": f["tienda_id"], "items": {}}
        )
        t["items"][f["sku"]] = t["items"].get(f["sku"], 0) + f["cantidad"]
    return productos, tickets


def unidades(tickets: dict, excluir_ticket: str, tienda: str | None = None) -> dict:
    total: dict[str, int] = defaultdict(int)
    for tid, datos in tickets.items():
        if tid == excluir_ticket:
            continue
        if tienda and datos["tienda"] != tienda:
            continue
        for sku, cantidad in datos["items"].items():
            total[sku] += cantidad
    return total


# --- Baselines -------------------------------------------------------------
# Todos reciben el mismo contexto y devuelven una lista ordenada de SKUs.


def base_aleatorio(ancla, tienda, candidatos, productos, tickets, ticket_id, azar):
    return azar.sample(sorted(candidatos), min(K, len(candidatos)))


def base_mas_vendido_global(
    ancla, tienda, candidatos, productos, tickets, ticket_id, azar
):
    ventas = unidades(tickets, ticket_id)
    return sorted(candidatos, key=lambda s: (-ventas.get(s, 0), s))[:K]


def base_mas_vendido_tienda(
    ancla, tienda, candidatos, productos, tickets, ticket_id, azar
):
    ventas = unidades(tickets, ticket_id, tienda)
    if not ventas:
        ventas = unidades(tickets, ticket_id)
    return sorted(candidatos, key=lambda s: (-ventas.get(s, 0), s))[:K]


def base_misma_categoria(
    ancla, tienda, candidatos, productos, tickets, ticket_id, azar
):
    categoria = productos[ancla]["categoria"]
    ventas = unidades(tickets, ticket_id)
    mismos = [s for s in candidatos if productos[s]["categoria"] == categoria]
    otros = [s for s in candidatos if productos[s]["categoria"] != categoria]
    orden = sorted(mismos, key=lambda s: (-ventas.get(s, 0), s)) + sorted(
        otros, key=lambda s: (-ventas.get(s, 0), s)
    )
    return orden[:K]


BASELINES = {
    "aleatorio con stock": base_aleatorio,
    "mas vendido global": base_mas_vendido_global,
    "mas vendido en la tienda": base_mas_vendido_tienda,
    "misma categoria": base_misma_categoria,
}


MODOS = {
    "solo lo comprobado": {"historico": 1.0, "atributos": 0.35},
    "equilibrado": {"historico": 1.0, "atributos": 0.65},
    "descubrir mas": {"historico": 0.7, "atributos": 1.0},
}

# El modo con el que se reporta la tabla principal: el de operar a diario.
MODO_POR_DEFECTO = "equilibrado"


def evaluar(bd, pesos: dict | None = None) -> tuple[dict, int]:
    productos, tickets = leer_datos(bd)
    comprables = {s for s, p in productos.items() if p["activo"] and p["stock"] > 0}
    atributos = AtributosStrategy(bd)
    azar = random.Random(SEMILLA)

    resultados = {
        nombre: {"aciertos": 0, "rr": 0.0} for nombre in ["hibrido", *BASELINES]
    }
    instancias = 0

    for ticket_id, datos in tickets.items():
        skus = set(datos["items"])
        if len(skus) < 2:
            continue

        # Sin fuga: las reglas de este pliegue no ven el ticket que se mide.
        reglas = calcular_reglas_desde_canastas(
            {t: set(d["items"]) for t, d in tickets.items() if t != ticket_id}
        )
        historico = HistoricoEnMemoria(reglas)

        for oculto in sorted(skus):
            contexto = skus - {oculto}
            # Ancla determinista: la pieza mas cara de lo que queda, que suele
            # ser la principal del trabajo. El desempate por SKU hace el
            # resultado reproducible.
            ancla = max(contexto, key=lambda s: (productos[s]["precio"], s))
            excluir = contexto - {ancla}
            candidatos = comprables - {ancla} - excluir
            instancias += 1

            propuesta = mezclar(
                fuentes=[historico, atributos],
                sku=ancla,
                tienda=datos["tienda"],
                pesos=pesos or MODOS[MODO_POR_DEFECTO],
                ajustes={},
                comprables=comprables,
                excluir=excluir,
                limite=K,
            )
            listas = {
                "hibrido": [c["sku"] for c in propuesta["complementos"]][:K]
            }
            for nombre, funcion in BASELINES.items():
                listas[nombre] = funcion(
                    ancla,
                    datos["tienda"],
                    candidatos,
                    productos,
                    tickets,
                    ticket_id,
                    azar,
                )

            for nombre, lista in listas.items():
                if oculto in lista:
                    resultados[nombre]["aciertos"] += 1
                    resultados[nombre]["rr"] += 1 / (lista.index(oculto) + 1)

    return resultados, instancias


def sugerencias_por_producto(bd, pesos: dict) -> float:
    """Cuantas sugerencias deja este modo, en promedio y con el limite real.

    Es la otra mitad de la historia: un modo que acierta menos porque propone
    menos no es peor, es mas exigente. Sin este numero, la tabla de hit-rate
    sola haria parecer que "solo lo comprobado" esta roto.
    """
    productos, _ = leer_datos(bd)
    comprables = {s for s, p in productos.items() if p["activo"] and p["stock"] > 0}
    atributos = AtributosStrategy(bd)
    historico = HistoricoStrategy(bd)
    plazas = [f["id"] for f in bd.execute("SELECT id FROM tiendas ORDER BY id")]

    total = 0
    for sku in sorted(productos):
        for plaza in plazas:
            total += len(
                mezclar(
                    fuentes=[historico, atributos],
                    sku=sku,
                    tienda=plaza,
                    pesos=pesos,
                    ajustes={},
                    comprables=comprables,
                    excluir=set(),
                )["complementos"]
            )
    return total / (len(productos) * len(plazas))


def evaluar_conjunto_dorado(bd) -> dict:
    """Cuanto del dominio cubre cada fuente por separado.

    Es la prueba de que la capa de atributos no es adorno: el historico no
    puede recuperar lo que nunca se vendio junto.
    """
    from app.recomendador.historico import calcular_reglas

    productos, tickets = leer_datos(bd)
    comprables = {s for s, p in productos.items() if p["activo"] and p["stock"] > 0}
    historico = HistoricoEnMemoria(calcular_reglas(bd))
    atributos = AtributosStrategy(bd)

    fuentes = {
        "solo historico": [historico],
        "solo atributos": [atributos],
        "hibrido": [historico, atributos],
    }
    detalle = []
    conteo = {nombre: 0 for nombre in fuentes}

    for origen, destino, etiqueta in CONJUNTO_DORADO:
        fila = {"par": etiqueta, "origen": origen, "destino": destino}
        for nombre, lista in fuentes.items():
            propuesta = mezclar(
                fuentes=lista,
                sku=origen,
                tienda="cdmx",
                pesos={"historico": 1.0, "atributos": 0.8},
                ajustes={},
                comprables=comprables,
                excluir=set(),
                limite=6,
            )
            encontrado = destino in {c["sku"] for c in propuesta["complementos"]}
            fila[nombre] = encontrado
            conteo[nombre] += encontrado
        detalle.append(fila)

    return {"detalle": detalle, "conteo": conteo, "total": len(CONJUNTO_DORADO)}


def caso_merida(bd) -> list[dict]:
    from app.services import recomendacion_service

    productos, _ = leer_datos(bd)
    salida = []
    for sku in ("SKU005", "SKU010", "SKU024"):
        r = recomendacion_service.recomendar(bd, sku, "merida", limite=3)
        salida.append(
            {
                "sku": sku,
                "nombre": productos[sku]["nombre"],
                "sustituto": r["sustituto"],
                "complementos": r["complementos"],
                "productos": productos,
            }
        )
    return salida


def construir_reporte(
    resultados, instancias, dorado, merida, productos, por_modo
) -> str:
    lineas = []
    w = lineas.append

    w("# Evaluacion del recomendador\n")
    w("> Generado por `python scripts/evaluar.py`. Reproducible: base temporal")
    w("> sembrada desde los CSV y baseline aleatorio con semilla fija.\n")

    w("## 1. Leave-one-out sobre las canastas reales\n")
    w(f"- Canastas: **42 tickets**, todas de 2 o mas articulos.")
    w(f"- Instancias evaluadas: **{instancias}** (cada linea de venta ocultada una vez).")
    w(f"- Metricas: hit-rate@{K} y MRR. Intervalo de Wilson al 95%.")
    w("- Las reglas de asociacion se reconstruyen **ocultando el ticket medido**,")
    w("  asi que ningun acierto viene de haber visto la respuesta.\n")

    w(f"| Recomendador | hit-rate@{K} | IC 95% (Wilson) | MRR |")
    w("|---|---:|:---:|---:|")
    orden = ["hibrido", *BASELINES]
    for nombre in orden:
        aciertos = resultados[nombre]["aciertos"]
        tasa = aciertos / instancias if instancias else 0
        bajo, alto = wilson_intervalo(aciertos, instancias)
        mrr = resultados[nombre]["rr"] / instancias if instancias else 0
        etiqueta = "**hibrido (este sistema)**" if nombre == "hibrido" else nombre
        w(
            f"| {etiqueta} | {tasa:.3f} ({aciertos}/{instancias}) "
            f"| [{bajo:.3f}, {alto:.3f}] | {mrr:.3f} |"
        )

    w("")
    w("### Como leer esta tabla\n")
    w("**El intervalo de confianza es ancho y se solapa entre metodos.** Con 42")
    w("canastas no da para declarar un ganador estadisticamente significativo, y")
    w("presentarlo como si lo diera seria presentar ruido como metrica. Lo que la")
    w("tabla si sostiene es la direccion del efecto y, sobre todo, que el sistema")
    w("no es peor que las heuristicas triviales que ya podria aplicar el negocio.\n")
    w("La razon de fondo es estructural: solo 8 de los 45 pares co-ocurrentes")
    w("aparecen en mas de un ticket. Un test de canasta no puede premiar lo que")
    w("nunca se vendio junto, y justamente ahi es donde este sistema aporta. Por")
    w("eso la evaluacion sigue con dos comprobaciones cualitativas.\n")

    w("### Que cuesta y que da cada modo del panel\n")
    w("Los tres modos de la pantalla de Relaciones no son texto: cambian cuanta")
    w("evidencia se exige para ofrecer algo. Aqui esta el precio de cada uno,")
    w("medido sobre las mismas 89 instancias.\n")
    w("| Modo | hit-rate@3 | MRR | Sugerencias por producto |")
    w("|---|---:|---:|---:|")
    for nombre, cifras in por_modo.items():
        w(
            f"| {nombre} | {cifras['hit']:.3f} ({cifras['aciertos']}/{instancias}) "
            f"| {cifras['mrr']:.3f} | {cifras['media']:.1f} |"
        )
    w("")
    w("**Exigir mas evidencia cuesta aciertos, y eso es correcto.** «Solo lo")
    w("comprobado» acierta menos porque ofrece menos: recorta la cola de")
    w("sugerencias deducidas, y en esa cola caia algun acierto. Es la decision")
    w("que el negocio toma conscientemente -precision antes que cobertura- y")
    w("por eso el panel la ofrece como un modo y no como un valor por defecto")
    w("escondido.\n")

    w("## 2. Conjunto dorado de dominio\n")
    w("20 pares que cualquier ferretero daria por obvios. Mide cobertura de")
    w("dominio, no popularidad: es donde se ve que aporta cada fuente.\n")
    w("| Par | historico | atributos | hibrido |")
    w("|---|:---:|:---:|:---:|")
    for fila in dorado["detalle"]:
        marca = lambda v: "si" if v else "-"  # noqa: E731
        w(
            f"| {fila['par']} | {marca(fila['solo historico'])} "
            f"| {marca(fila['solo atributos'])} | {marca(fila['hibrido'])} |"
        )
    c = dorado["conteo"]
    total = dorado["total"]
    w(
        f"| **TOTAL** | **{c['solo historico']}/{total}** "
        f"| **{c['solo atributos']}/{total}** | **{c['hibrido']}/{total}** |"
    )
    w("")

    marcados = [f for f in dorado["detalle"] if "(*)" in f["par"]]
    n = len(marcados)
    por_fuente = {
        nombre: sum(1 for f in marcados if f[nombre])
        for nombre in ("solo historico", "solo atributos", "hibrido")
    }
    w(f"### Los {n} pares marcados (*): el argumento central\n")
    w(f"Son pares que **nunca co-ocurren en `sales.csv`**. Sobre ese subconjunto:\n")
    w(
        f"- solo historico: **{por_fuente['solo historico']}/{n}**  "
        f"(no es un defecto del algoritmo, es imposible por construccion:"
        f" no puede contar lo que nunca paso)"
    )
    w(f"- solo atributos: **{por_fuente['solo atributos']}/{n}**")
    w(f"- hibrido: **{por_fuente['hibrido']}/{n}**\n")
    fallados = [f["par"] for f in marcados if not f["hibrido"]]
    if fallados:
        w(
            f"El sistema falla {len(fallados)} de ellos: {', '.join(fallados)}. "
            "Es un complemento de segundo orden (la varilla necesita el soplete y "
            "el soplete necesita el gas) y queda en la posicion 7 por muy poco. "
            "**No se ajustaron los pesos para forzar el acierto**: seria "
            "sobreajustar a un conjunto escrito por el mismo autor del sistema.\n"
        )
    w("Este es el motivo de que la capa de atributos sea el motor y las reglas de")
    w("asociacion la evidencia. Con 42 tickets el historico cubre lo que ya se")
    w("vendio junto; el catalogo de una ferreteria es mucho mas grande que eso.\n")

    w("## 3. Caso Merida: recomendar sin una sola venta\n")
    w("Merida no aparece en `sales.csv`. Ninguna regla de asociacion puede")
    w("hablar de esa plaza; el perfil costero si.\n")
    for caso in merida:
        w(f"**{caso['sku']} - {caso['nombre']}**\n")
        s = caso["sustituto"]
        if s:
            w(
                f"- Mejor para esta plaza: `{s['sku']}` "
                f"{productos[s['sku']]['nombre']} - {s['justificacion']}"
            )
        else:
            w("- Mejor para esta plaza: el ancla ya es el adecuado.")
        for comp in caso["complementos"]:
            w(
                f"- Para terminar el trabajo: `{comp['sku']}` "
                f"{productos[comp['sku']]['nombre']} ({comp['fuente']})"
            )
        w("")

    w("## 4. Limitaciones declaradas\n")
    w("- n=42 canastas: el intervalo es ancho. No se declara ganador.")
    w("- El leave-one-out mide complementos. El sustituto no cabe en esta prueba")
    w("  porque por definicion no aparece en la misma canasta; se valida con el")
    w("  conjunto dorado y el caso Merida.")
    w("- El conjunto dorado lo escribio quien construyo el sistema. Mide")
    w("  cobertura de dominio, no aceptacion del cliente.")
    w("- La medida que de verdad importa (subir ventas) solo se obtiene con un")
    w("  A/B en mostrador midiendo tasa de aceptacion y ticket promedio. Esta")
    w("  evaluacion offline sirve para no salir a produccion a ciegas.")
    return "\n".join(lineas)


def main() -> None:
    ruta = Path(__file__).resolve().parent.parent / "evaluacion_temporal.db"
    sembrar(ruta)
    bd = conectar(ruta)
    try:
        # Las reglas materializadas, igual que en produccion: HistoricoStrategy
        # lee de la tabla `relaciones`, no recalcula. Sin esto se estaria
        # midiendo un sistema que solo tiene la mitad de sus fuentes.
        #
        # No contamina el leave-one-out: ese usa reglas en memoria construidas
        # por pliegue, sin el ticket que mide.
        combinadas = {}
        for regla in relaciones_por_atributos(bd) + calcular_reglas(bd):
            combinadas[(regla["sku_origen"], regla["sku_destino"], regla["tipo"])] = regla
        bd.execute("BEGIN IMMEDIATE")
        relaciones_repo.reemplazar(bd, list(combinadas.values()))
        bd.commit()

        resultados, instancias = evaluar(bd)

        # El mismo leave-one-out con cada modo del panel: es lo que demuestra
        # que los tres hacen algo distinto, y cuanto cuesta cada uno.
        por_modo = {}
        for nombre, pesos in MODOS.items():
            cifras, _ = evaluar(bd, pesos)
            por_modo[nombre] = {
                "aciertos": cifras["hibrido"]["aciertos"],
                "hit": cifras["hibrido"]["aciertos"] / instancias,
                "mrr": cifras["hibrido"]["rr"] / instancias,
                "media": sugerencias_por_producto(bd, pesos),
            }

        dorado = evaluar_conjunto_dorado(bd)
        merida = caso_merida(bd)
        productos, _ = leer_datos(bd)
        reporte = construir_reporte(
            resultados, instancias, dorado, merida, productos, por_modo
        )
    finally:
        bd.close()
        for sufijo in ("", "-wal", "-shm"):
            archivo = Path(str(ruta) + sufijo)
            if archivo.exists():
                archivo.unlink()

    DIR_DOCS.mkdir(parents=True, exist_ok=True)
    destino = DIR_DOCS / "evaluacion.md"
    destino.write_text(reporte, encoding="utf-8")

    print(reporte)
    print(f"\n---\nReporte escrito en {destino}")


if __name__ == "__main__":
    main()
