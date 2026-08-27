"""El LLM como analista del negocio, no como redactor ni como recomendador.

QUE HACE Y QUE NO
-----------------
NO propone "ofrece X junto con Y": de eso ya se encarga el recomendador, que es
determinista, evaluable y no cuesta una llamada. Repetirlo con un modelo seria
pagar por la misma respuesta peor fundamentada.

Lo que hace es LEER LOS NUMEROS y decir que significan: como va esta plaza
frente a la cadena, donde hay dinero parado, si el catalogo encaja con el clima
de la zona, y si el propio sistema de recomendacion esta funcionando ahi. Eso
no sale de ninguna consulta, porque no es contar: es interpretar.

Por eso el retrato que recibe trae metricas ya calculadas. Un modelo sumando
columnas se equivoca; un modelo explicando una suma que ya viene hecha, no.
"""

import json

from .cliente import pedir_json

# Topes de la respuesta. El modelo tiende a la lista larga y un panel con doce
# puntos no se lee. Se recorta aqui, no en la interfaz: es parte del contrato.
MAXIMO_PUNTOS = 4
MAXIMO_DECISIONES = 3
LARGO_TITULO = 90
LARGO_TEXTO = 400

INSTRUCCION = """Eres analista de negocio de una ferreteria mexicana con cinco
sucursales que comparten un mismo inventario. Te dan los datos de UNA sucursal
y escribes para el encargado de esa tienda.

Tu trabajo es INTERPRETAR, no listar. Los datos ya vienen contados: participacion
en las ventas, rotacion, valor del inventario, que se vende y que no. Lo que
falta es alguien que diga que significan y que decision toca.

NO propongas "vende el producto X junto con el Y". De eso ya se encarga el
sistema de recomendacion, y sus sugerencias tambien te las paso para que las
tengas en cuenta. Si repites eso, no aportas nada.

Analiza dos cosas distintas:

1. EL NEGOCIO. Como va esta plaza comparada con la cadena. Donde esta el dinero
   quieto. Que parte del catalogo no se mueve y cuanto vale. Si lo que se vende
   aqui encaja con el clima y el tipo de cliente de esta zona. Si la venta esta
   concentrada en pocos productos y que riesgo trae eso.

2. EL SISTEMA. Si el motor de recomendaciones esta pudiendo trabajar en esta
   plaza: de cuantas ventas reales se esta apoyando, cuanto depende de deducir
   por el tipo de producto, y que se le esta escapando. Una sucursal sin
   historico no es igual a una con cuarenta tickets, y eso cambia cuanto hay
   que fiarse de lo que propone.

Reglas estrictas:
- Espanol de Mexico. Frases cortas y directas. Nada de marketing ni de relleno.
- Cada punto se apoya en un dato de la entrada, y ese dato lo citas en "dato".
- No inventes cifras, productos ni ventas. Si no esta en los datos, no existe.
- Nada de generalidades tipo "mejorar la atencion" o "capacitar al personal".
- Si un numero es pequeno, dilo: con 42 tickets en toda la cadena no se puede
  concluir lo mismo que con cuarenta mil. Preferimos que digas "no alcanza para
  afirmarlo" a que inventes una tendencia.

Devuelve SOLO este JSON:
{
  "resumen": "dos o tres frases: como esta esta plaza y que es lo primero que ves",
  "negocio": [
    {"titulo": "que pasa, en pocas palabras",
     "analisis": "por que pasa y que implica",
     "dato": "el numero concreto en el que te apoyas",
     "impacto": "alto|medio|bajo",
     "skus": ["SKU001"]}
  ],
  "sistema": [
    {"titulo": "...", "analisis": "...", "dato": "...",
     "impacto": "alto|medio|bajo", "skus": []}
  ],
  "decisiones": [
    {"titulo": "la decision, no la tarea",
     "porque": "en que se apoya",
     "accion": "que hacer esta semana"}
  ]
}

Maximo cuatro puntos de negocio, cuatro de sistema y tres decisiones. Mejor dos
buenos que seis tibios; si de algo no tienes evidencia, no lo pongas.

DATOS DE LA SUCURSAL:
"""


def _texto(valor: object, tope: int) -> str:
    return " ".join(str(valor or "").split())[:tope]


def _punto(crudo: dict) -> dict | None:
    """Un punto del analisis, saneado. Sin titulo ni analisis no dice nada."""
    titulo = _texto(crudo.get("titulo"), LARGO_TITULO)
    analisis = _texto(crudo.get("analisis"), LARGO_TEXTO)
    if not titulo or not analisis:
        return None
    impacto = str(crudo.get("impacto", "medio")).lower()
    return {
        "titulo": titulo,
        "analisis": analisis,
        "dato": _texto(crudo.get("dato"), 160),
        "impacto": impacto if impacto in ("alto", "medio", "bajo") else "medio",
        "skus": [
            _texto(sku, 24).upper() for sku in (crudo.get("skus") or []) if _texto(sku, 24)
        ][:6],
    }


def _decision(crudo: dict) -> dict | None:
    titulo = _texto(crudo.get("titulo"), LARGO_TITULO)
    accion = _texto(crudo.get("accion"), LARGO_TEXTO)
    if not titulo or not accion:
        return None
    return {
        "titulo": titulo,
        "porque": _texto(crudo.get("porque"), LARGO_TEXTO),
        "accion": accion,
    }


def _lista(crudos: object, convertir, tope: int) -> list[dict]:
    convertidos = (convertir(c) for c in (crudos or []) if isinstance(c, dict))
    return [c for c in convertidos if c][:tope]


def analizar(retrato: dict) -> dict:
    """Una llamada, un analisis validado.

    Lo que el modelo devuelva se recorta y se filtra antes de guardarse: un
    texto de 4000 caracteres, un campo que falta o una lista de quince puntos
    no pueden romper la pantalla del encargado ni quedar guardados como validos.
    """
    crudo = pedir_json(INSTRUCCION + json.dumps(retrato, ensure_ascii=False, indent=1))

    return {
        "resumen": _texto(crudo.get("resumen"), 600),
        "negocio": _lista(crudo.get("negocio"), _punto, MAXIMO_PUNTOS),
        "sistema": _lista(crudo.get("sistema"), _punto, MAXIMO_PUNTOS),
        "decisiones": _lista(crudo.get("decisiones"), _decision, MAXIMO_DECISIONES),
    }
