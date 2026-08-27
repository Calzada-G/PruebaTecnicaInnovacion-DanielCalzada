"""Analisis del sistema con IA, con una sola llamada y solo si hace falta.

DOS DECISIONES QUE SOSTIENEN ESTO
---------------------------------
1. **Una llamada, no una por relacion.** El modelo recibe el sistema entero de
   una plaza y devuelve un unico analisis. Reescribir frases una a una gasta
   una llamada por fila para cambiar como suena algo que el sistema ya sabia;
   esto gasta una para producir algo que no sabia.

2. **No se llama si nada cambio.** Antes de preguntar se calcula la HUELLA del
   estado: catalogo, existencias, ventas por plaza, relaciones, ajustes del
   negocio y pesos. Si coincide con la del ultimo analisis guardado, la
   respuesta ya esta escrita y se devuelve tal cual, sin tocar la red. La
   garantia vive aqui y no en el boton de la interfaz: asi no depende de que
   nadie se acuerde de comprobarlo.

El modelo NO decide que se recomienda. El ranking sigue siendo determinista y
evaluable; esto es una opinion sobre el negocio, guardada y etiquetada como
tal.
"""

import hashlib
import json
import sqlite3

from ..config import GEMINI_MODEL
from ..errores import TiendaNoEncontrada
from ..ia import analista, cliente
from ..repositories import (
    analisis_repo,
    productos_repo,
    relaciones_repo,
    tiendas_repo,
    ventas_repo,
)
from . import diagnostico_service

# Cuantos pares historicos se le pasan al modelo. Con 42 tickets, mas alla de
# los diez primeros el soporte es 1 y ya no distingue senal de casualidad.
PARES_AL_MODELO = 10


def _porcentaje(parte: float, total: float) -> float:
    return round(100 * parte / total, 1) if total else 0.0


def _retrato(bd: sqlite3.Connection, plaza: sqlite3.Row) -> dict:
    """Todo lo que el modelo necesita saber, y nada mas.

    Las cuentas van HECHAS. Un modelo sumando columnas se equivoca y no hay
    forma de saberlo; un modelo explicando una suma que ya viene calculada, no.
    Eso ademas convierte la pregunta en analitica -"que significa este 12%"- en
    vez de aritmetica.
    """
    tienda_id = plaza["id"]
    unidades_plaza = ventas_repo.unidades_por_sku(bd, tienda_id)
    unidades_cadena = ventas_repo.unidades_por_sku(bd)
    productos = [dict(p) for p in productos_repo.listar(bd)]
    diagnostico = diagnostico_service.diagnosticar(bd, tienda_id)

    catalogo = [
        {
            "sku": p["sku"],
            "nombre": p["nombre"],
            "categoria": p["categoria"],
            "material": p["material"],
            "uso": p["uso_recomendado"],
            "precio": p["precio"],
            "existencia": p["stock"],
            "valor_inmovilizado": round(p["precio"] * p["stock"], 2),
            "vendidos_aqui": unidades_plaza.get(p["sku"], 0),
            "vendidos_en_la_cadena": unidades_cadena.get(p["sku"], 0),
        }
        for p in productos
    ]

    vendidas_aqui = sum(unidades_plaza.values())
    vendidas_cadena = sum(unidades_cadena.values())
    valor_total = sum(c["valor_inmovilizado"] for c in catalogo)
    parados = [c for c in catalogo if c["vendidos_en_la_cadena"] == 0]
    sin_salida_aqui = [c for c in catalogo if c["vendidos_aqui"] == 0]
    mas_vendidos = sorted(catalogo, key=lambda c: -c["vendidos_aqui"])[:5]

    ingreso_estimado = sum(
        c["precio"] * c["vendidos_aqui"] for c in catalogo
    )
    tickets_aqui = diagnostico["tickets_en_la_plaza"]

    relaciones = relaciones_repo.listar(bd)
    historicas = sorted(
        (r for r in relaciones if r["fuente"] == "historico" and r["soporte"]),
        key=lambda r: -r["soporte"],
    )[:PARES_AL_MODELO]
    con_sugerencia = {r["sku_origen"] for r in relaciones if r["estado"] != "bloqueada"}

    return {
        "plaza": {
            "nombre": plaza["nombre"],
            "clima_y_tipo_de_cliente": plaza["perfil"],
            "tickets_aqui": tickets_aqui,
            "tickets_en_la_cadena": diagnostico["tickets_en_la_cadena"],
            "participacion_en_tickets_pct": _porcentaje(
                tickets_aqui, diagnostico["tickets_en_la_cadena"]
            ),
        },
        "aviso_sobre_los_datos": (
            "El historico completo son 42 tickets. Es poco: sirve para orientar, "
            "no para afirmar tendencias."
        ),
        "inventario": {
            "es_compartido_entre_las_5_sucursales": True,
            "valor_total": round(valor_total, 2),
            "productos_activos": len(catalogo),
            "sin_una_sola_venta_en_la_cadena": len(parados),
            "valor_de_lo_que_nunca_se_vendio": round(
                sum(c["valor_inmovilizado"] for c in parados), 2
            ),
            "sin_venta_en_esta_plaza": len(sin_salida_aqui),
            "valor_de_lo_que_no_sale_aqui": round(
                sum(c["valor_inmovilizado"] for c in sin_salida_aqui), 2
            ),
            "agotados": sum(1 for c in catalogo if c["existencia"] == 0),
        },
        "ventas_de_esta_plaza": {
            "unidades": vendidas_aqui,
            "participacion_en_unidades_pct": _porcentaje(
                vendidas_aqui, vendidas_cadena
            ),
            "ingreso_estimado": round(ingreso_estimado, 2),
            "ticket_promedio_estimado": (
                round(ingreso_estimado / tickets_aqui, 2) if tickets_aqui else 0
            ),
            "nota": "Estimado con los precios de hoy; las ventas no guardan precio historico.",
            "concentracion_top5_pct": _porcentaje(
                sum(c["vendidos_aqui"] for c in mas_vendidos), vendidas_aqui
            ),
            "mas_vendidos_aqui": [
                {"sku": c["sku"], "nombre": c["nombre"], "unidades": c["vendidos_aqui"]}
                for c in mas_vendidos
                if c["vendidos_aqui"]
            ],
        },
        "catalogo": catalogo,
        "sistema_de_recomendacion": {
            "como_funciona": (
                "Mezcla dos fuentes: 'historico' (pares que ya se vendieron juntos) "
                "y 'atributos' (deduce por material y clima de la plaza cuando no "
                "hay ventas que lo respalden)."
            ),
            "relaciones_totales": len(relaciones),
            "apoyadas_en_ventas": sum(
                1 for r in relaciones if r["fuente"] == "historico"
            ),
            "deducidas_por_atributos": sum(
                1 for r in relaciones if r["fuente"] == "atributos"
            ),
            "bloqueadas_por_el_negocio": sum(
                1 for r in relaciones if r["estado"] == "bloqueada"
            ),
            "productos_sin_nada_que_sugerir": len(
                [c for c in catalogo if c["sku"] not in con_sugerencia]
            ),
            "pesos_configurados": relaciones_repo.pesos(bd),
            "pares_que_ya_se_venden_juntos": [
                {
                    "origen": r["nombre_origen"],
                    "destino": r["nombre_destino"],
                    "tickets": r["soporte"],
                }
                for r in historicas
            ],
        },
        "ya_detectado_automaticamente": [
            {"titulo": h["titulo"], "accion": h["accion"]}
            for h in diagnostico["hallazgos"]
        ],
    }


def _huella(retrato: dict) -> str:
    """Identifica el estado del sistema que se va a analizar.

    Cambia si cambia un precio, una existencia, una venta, una relacion, un
    bloqueo o un peso. No cambia si solo pasa el tiempo: preguntar dos veces lo
    mismo devuelve lo mismo y no vale una llamada.

    `sort_keys` es lo que la hace estable: sin eso, dos diccionarios iguales
    con las claves en otro orden darian huellas distintas y el cache no
    acertaria nunca.
    """
    canonico = json.dumps(retrato, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonico.encode("utf-8")).hexdigest()[:32]


def _empaquetar(fila: sqlite3.Row, desde_cache: bool, vigente: bool) -> dict:
    return {
        "analisis": json.loads(fila["contenido"]),
        "modelo": fila["modelo"],
        "generado_en": fila["creado_en"],
        "huella": fila["huella"],
        "desde_cache": desde_cache,
        "vigente": vigente,
    }


def consultar(bd: sqlite3.Connection, tienda: str) -> dict:
    """Lo que hay guardado, sin llamar nunca al modelo.

    `vigente` dice si el analisis sigue describiendo el sistema actual. Es lo
    que permite que el boton se apague solo cuando no hay nada nuevo que
    analizar.
    """
    plaza = tiendas_repo.obtener(bd, tienda)
    if plaza is None:
        raise TiendaNoEncontrada(tienda)

    huella = _huella(_retrato(bd, plaza))
    fila = analisis_repo.ultimo(bd, tienda)
    if fila is None:
        return {
            "tienda": tienda,
            "disponible": cliente.hay_clave(),
            "hay_analisis": False,
            "vigente": False,
            "huella_actual": huella,
        }

    return {
        "tienda": tienda,
        "disponible": cliente.hay_clave(),
        "hay_analisis": True,
        "huella_actual": huella,
        **_empaquetar(fila, desde_cache=True, vigente=fila["huella"] == huella),
    }


def generar(bd: sqlite3.Connection, tienda: str) -> dict:
    """Devuelve el analisis; solo llama al modelo si el sistema cambio."""
    plaza = tiendas_repo.obtener(bd, tienda)
    if plaza is None:
        raise TiendaNoEncontrada(tienda)

    retrato = _retrato(bd, plaza)
    huella = _huella(retrato)

    guardado = analisis_repo.por_huella(bd, tienda, huella)
    if guardado is not None:
        # Nada cambio desde la ultima vez: la respuesta ya esta escrita.
        return {
            "tienda": tienda,
            "disponible": cliente.hay_clave(),
            "hay_analisis": True,
            "huella_actual": huella,
            **_empaquetar(guardado, desde_cache=True, vigente=True),
        }

    contenido = analista.analizar(retrato)

    cur = bd.cursor()
    cur.execute("BEGIN IMMEDIATE")
    try:
        analisis_repo.guardar(
            bd,
            tienda,
            huella,
            GEMINI_MODEL,
            json.dumps(contenido, ensure_ascii=False),
        )
        bd.commit()
    except Exception:
        bd.rollback()
        raise

    return {
        "tienda": tienda,
        "disponible": True,
        "hay_analisis": True,
        "huella_actual": huella,
        **_empaquetar(analisis_repo.por_huella(bd, tienda, huella), False, True),
    }
