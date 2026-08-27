"""Lo que le falta a una plaza, dicho por el sistema sin que nadie pregunte.

El resto de la API responde preguntas: dame el catalogo, recomiendame algo.
Esto es lo contrario. La sucursal no pregunta nada y el sistema le dice que no
esta funcionando: que no se ha vendido, que se agoto, que material no aguanta
el clima de la zona y que producto convendria dar de alta.

Nace del caso Merida -cero tickets en sales.csv- pero no es un caso especial
escrito a mano para esa tienda: la falta de historico es solo uno de los
hallazgos y se calcula igual para las cinco. Si manana Merida vende, el aviso
desaparece solo.

Todo se deriva de datos que ya existen (ventas, productos, relaciones): no hay
ninguna tabla nueva ni nada capturado a mano.
"""

import sqlite3

from ..errores import TiendaNoEncontrada
from ..recomendador.perfiles import ADECUACION, PLAZA_TEXTO, adecuacion, ambiente
from ..repositories import productos_repo, relaciones_repo, tiendas_repo, ventas_repo

# Por debajo de esta adecuacion (0 a 1, la tabla de perfiles.py) el material de
# un producto no es el que pide la plaza.
ADECUACION_MINIMA = 0.5

# A partir de aqui el encargado todavia tiene margen para reponer.
POCAS_PIEZAS = 5

# Cuantos productos se citan por hallazgo. El panel es una ayuda para decidir,
# no un inventario: con seis nombres ya se entiende el problema.
MAXIMO_CITADOS = 6

# Un par que solo aparecio en un ticket no es una promocion, es una casualidad.
SOPORTE_MINIMO_PROMOCION = 2

# Que producto le falta a cada plaza, en la frase que se lee en el panel.
#
# No se reutiliza VENTAJA_AMBIENTE de perfiles.py aunque se le parezca: aquel
# describe la ventaja de un sustituto que YA existe ("resiste corrosion
# salina"), y este pide un alta que todavia no esta en el catalogo.
FALTA_EN_LA_PLAZA = {
    "costero": "resista la corrosión salina",
    "sol": "resista la radiación solar directa",
    "humedad": "resista la humedad y la intemperie",
    "interior": "sea de interior y más barata",
    "neutro": "sirva en cualquier plaza",
}


def _segun(cantidad: int, uno: str, varios: str) -> str:
    """Titulo en singular o en plural.

    Estos textos se leen tal cual en la interfaz, y un "1 productos" delata que
    la frase la armo una concatenacion que nadie volvio a leer.
    """
    return f"{cantidad} {uno if cantidad == 1 else varios}"


def _hallazgo(
    clave: str,
    nivel: str,
    titulo: str,
    detalle: str,
    accion: str,
    productos: list[dict] | None = None,
) -> dict:
    citados = productos or []
    return {
        "clave": clave,
        "nivel": nivel,
        "titulo": titulo,
        "detalle": detalle,
        "accion": accion,
        "total": len(citados),
        "productos": [
            {"sku": p["sku"], "nombre": p["nombre"]} for p in citados[:MAXIMO_CITADOS]
        ],
    }


def _ambiente_que_pide(perfil: str) -> str:
    """El ambiente mejor puntuado del perfil: lo que esta plaza necesita."""
    tabla = ADECUACION.get(perfil, ADECUACION["interior_urbano"])
    return max(tabla, key=lambda amb: tabla[amb])


def _mejor_pareja(
    bd: sqlite3.Connection, activos: dict[str, dict]
) -> tuple[dict, dict, int] | None:
    """La relacion historica con mas tickets detras y ambos productos vendibles."""
    candidatas = [
        f
        for f in relaciones_repo.listar(bd, tipo="complemento", fuente="historico")
        if f["estado"] != "bloqueada"
        and (f["soporte"] or 0) >= SOPORTE_MINIMO_PROMOCION
        and f["sku_origen"] in activos
        and f["sku_destino"] in activos
        and activos[f["sku_origen"]]["stock"] > 0
        and activos[f["sku_destino"]]["stock"] > 0
    ]
    if not candidatas:
        return None
    mejor = max(candidatas, key=lambda f: f["soporte"])
    return (
        activos[mejor["sku_origen"]],
        activos[mejor["sku_destino"]],
        mejor["soporte"],
    )


def diagnosticar(bd: sqlite3.Connection, tienda: str) -> dict:
    plaza = tiendas_repo.obtener(bd, tienda)
    if plaza is None:
        raise TiendaNoEncontrada(tienda)

    perfil = plaza["perfil"]
    nombre_plaza = plaza["nombre"]
    texto_plaza = PLAZA_TEXTO.get(perfil, "de uso general")

    activos = [dict(f) for f in productos_repo.listar(bd)]
    tickets_plaza = ventas_repo.contar_tickets(bd, tienda)
    tickets_cadena = ventas_repo.contar_tickets(bd)
    unidades_cadena = ventas_repo.unidades_por_sku(bd)
    unidades_plaza = ventas_repo.unidades_por_sku(bd, tienda)

    hallazgos: list[dict] = []

    # --- Lo que impide aprender ---------------------------------------------
    if tickets_plaza == 0:
        hallazgos.append(
            _hallazgo(
                "plaza_sin_historial",
                "alerta",
                f"{nombre_plaza} no tiene ni un ticket registrado",
                f"De los {tickets_cadena} tickets del histórico, ninguno es de esta "
                "sucursal. Aquí el sistema no sabe qué se lleva junto: todo lo que "
                "propone sale de los atributos del producto y del clima de la plaza.",
                "Cobra desde el mostrador o carga el histórico de esta tienda. En "
                "cuanto haya tickets, las sugerencias empiezan a respaldarse en "
                "ventas reales y no solo en el material.",
            )
        )

    nunca_vendidos = [p for p in activos if not unidades_cadena.get(p["sku"])]
    if nunca_vendidos:
        hallazgos.append(
            _hallazgo(
                "nunca_vendido",
                "alerta",
                _segun(
                    len(nunca_vendidos),
                    "producto del catálogo no se ha vendido nunca",
                    "productos del catálogo no se han vendido nunca",
                ),
                "En toda la cadena no hay un solo ticket con ellos, así que el "
                "sistema no puede aprender con qué se acompañan. Hoy se recomiendan "
                "únicamente por sus atributos.",
                "Revisa que su uso recomendado esté bien escrito: ese campo es de "
                "donde salen sus sugerencias mientras no tengan ventas.",
                nunca_vendidos,
            )
        )

    # Con la plaza a cero esta lista seria el catalogo entero, y no diria nada
    # que no diga ya el hallazgo anterior.
    if tickets_plaza:
        aqui_no = [
            p
            for p in activos
            if unidades_cadena.get(p["sku"]) and not unidades_plaza.get(p["sku"])
        ]
        aqui_no.sort(key=lambda p: unidades_cadena[p["sku"]], reverse=True)
        if aqui_no:
            hallazgos.append(
                _hallazgo(
                    "sin_venta_en_la_plaza",
                    "aviso",
                    _segun(
                        len(aqui_no),
                        "producto se vende en otras sucursales y aquí no",
                        "productos se venden en otras sucursales y aquí no",
                    ),
                    "Están en el mismo inventario compartido y con existencia, pero "
                    f"en {nombre_plaza} no se ha cobrado ninguno. Los primeros de la "
                    "lista son los que más se mueven en el resto de la cadena.",
                    "Empieza por ofrecerlos. Si tampoco salen aquí, ya es información "
                    "útil para decidir dónde conviene tener el inventario.",
                    aqui_no,
                )
            )

    # --- Lo que no se puede vender ------------------------------------------
    agotados = [p for p in activos if p["stock"] == 0]
    if agotados:
        hallazgos.append(
            _hallazgo(
                "sin_existencia",
                "alerta",
                _segun(
                    len(agotados), "producto sin existencia", "productos sin existencia"
                ),
                "Están fuera del mostrador y también fuera de las recomendaciones: "
                "el sistema nunca propone algo que no se puede cobrar.",
                "Cada uno es una venta que hoy no se puede cerrar. Repón, o da de "
                "baja para que dejen de ocupar el catálogo.",
                agotados,
            )
        )

    por_agotarse = sorted(
        (p for p in activos if 0 < p["stock"] <= POCAS_PIEZAS),
        key=lambda p: p["stock"],
    )
    if por_agotarse:
        hallazgos.append(
            _hallazgo(
                "por_agotarse",
                "aviso",
                _segun(
                    len(por_agotarse),
                    f"producto con {POCAS_PIEZAS} piezas o menos",
                    f"productos con {POCAS_PIEZAS} piezas o menos",
                ),
                "Al llegar a cero salen del mostrador y de las sugerencias, aunque "
                "sean lo que el sistema más propone.",
                "Reponer antes de que se agoten cuesta menos que perder la venta.",
                por_agotarse,
            )
        )

    # --- Lo que el catalogo no cubre para esta plaza -------------------------
    # Tener un sustituto no basta: cuenta solo si ese sustituto si le sirve a
    # esta plaza. Un tornillo de interior recambiado por otro de interior deja
    # a Merida igual de descubierta.
    por_sku = {p["sku"]: p for p in activos}

    def sirve_aqui(producto: dict) -> float:
        return adecuacion(
            perfil, ambiente(producto["uso_recomendado"], producto["material"])
        )

    con_recambio = {
        f["sku_origen"]
        for f in relaciones_repo.listar(bd, tipo="sustituto")
        if f["estado"] != "bloqueada"
        and f["sku_destino"] in por_sku
        and por_sku[f["sku_destino"]]["stock"] > 0
        and sirve_aqui(por_sku[f["sku_destino"]]) >= ADECUACION_MINIMA
    }
    sin_recambio = [
        p
        for p in activos
        if p["sku"] not in con_recambio and sirve_aqui(p) < ADECUACION_MINIMA
    ]
    if sin_recambio:
        falta = FALTA_EN_LA_PLAZA.get(_ambiente_que_pide(perfil), "aguante más")
        hallazgos.append(
            _hallazgo(
                "sin_recambio_para_la_plaza",
                "aviso",
                _segun(
                    len(sin_recambio),
                    "producto no es para el clima de aquí y no tiene recambio",
                    "productos no son para el clima de aquí y no tienen recambio",
                ),
                f"{nombre_plaza} es una plaza {texto_plaza}, y de estos productos no "
                "existe en el catálogo una versión mejor para la zona. El sistema los "
                "ofrece igual porque no hay otra cosa que ofrecer.",
                f"Dar de alta la versión que {falta} es la mejora con más efecto en "
                "ventas para esta sucursal.",
                sin_recambio,
            )
        )

    con_relacion = {f["sku_origen"] for f in relaciones_repo.listar(bd)}
    huerfanos = [p for p in activos if p["sku"] not in con_relacion]
    if huerfanos:
        hallazgos.append(
            _hallazgo(
                "sin_nada_que_ofrecer",
                "aviso",
                _segun(
                    len(huerfanos),
                    "producto no tiene nada que sugerir al lado",
                    "productos no tienen nada que sugerir al lado",
                ),
                "Ni por ventas ni por atributos: al venderlos, el mostrador no propone "
                "acompañamiento y el ticket se queda en una sola pieza.",
                "Casi siempre es el uso recomendado, demasiado genérico para "
                "emparentarlo con nada. Concrétalo y la relación aparece sola.",
                huerfanos,
            )
        )

    # --- Lo que si esta funcionando -----------------------------------------
    pareja = _mejor_pareja(bd, {p["sku"]: p for p in activos})
    if pareja:
        origen, destino, soporte = pareja
        hallazgos.append(
            _hallazgo(
                "promocion_con_respaldo",
                "oportunidad",
                f"Paquete con respaldo: {origen['nombre']} + {destino['nombre']}",
                f"Es la pareja que más veces se ha ido junta: {soporte} tickets de "
                f"los {tickets_cadena} del histórico. Los dos tienen existencia.",
                "Un precio de paquete convierte la sugerencia del mostrador en una "
                "razón para decir que sí.",
                [origen, destino],
            )
        )

    return {
        "tienda": plaza["id"],
        "nombre": nombre_plaza,
        "perfil": perfil,
        "tickets_en_la_plaza": tickets_plaza,
        "tickets_en_la_cadena": tickets_cadena,
        "productos_activos": len(activos),
        "hallazgos": hallazgos,
    }
