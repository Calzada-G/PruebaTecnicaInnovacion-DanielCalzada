"""Unica salida a Internet del proyecto: la llamada a Gemini.

Aislada aqui para que el resto del backend no sepa que existe una red. Los
servicios piden un analisis; si no hay clave, si la red falla o si el modelo
devuelve basura, reciben una excepcion de dominio y deciden que hacer.
"""

import json
import time

import httpx

from ..config import GEMINI_API_KEY, GEMINI_MODEL
from ..errores import IANoDisponible

URL = "https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent"

# El tier gratuito devuelve 429 y 503 por saturacion. Son fallos transitorios,
# no errores de la peticion.
REINTENTABLES = (429, 500, 502, 503, 504)
ESPERAS = (2, 6)

TIEMPO_LIMITE = 90.0


def hay_clave() -> bool:
    """Sin clave el sistema entero sigue funcionando; solo falta el analisis."""
    return bool(GEMINI_API_KEY)


def sin_clave(texto: str) -> str:
    """Nunca dejar la credencial en un mensaje de error.

    httpx incluye la URL completa en el texto de sus excepciones. Con la clave
    en cabecera no deberia aparecer, pero un mensaje de error acaba en un log y
    en una respuesta HTTP: se sanea igual.
    """
    return texto.replace(GEMINI_API_KEY, "***") if GEMINI_API_KEY else texto


# La latencia la manda el texto que el modelo ESCRIBE, no el que lee. Medido
# con el retrato completo de una plaza (6000 tokens de entrada): 3.7s sin tope
# y 3.1s con el. Ademas evita que un dia devuelva quince puntos de mil
# caracteres que de todas formas se van a recortar al guardarlos.
MAXIMO_TOKENS_SALIDA = 900


def pedir_json(instruccion: str, temperatura: float = 0.3) -> dict:
    """Una peticion, una respuesta JSON ya parseada.

    `responseMimeType` obliga al modelo a devolver JSON: sin eso responde con
    el JSON envuelto en un bloque de codigo y hay que recortarlo a mano, que
    falla el dia que cambia el formato del envoltorio.
    """
    if not hay_clave():
        raise IANoDisponible(
            "No hay GEMINI_API_KEY configurada. El resto del sistema funciona igual."
        )

    cuerpo = {
        "contents": [{"parts": [{"text": instruccion}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": temperatura,
            "maxOutputTokens": MAXIMO_TOKENS_SALIDA,
            # Explicito, no por defecto: los modelos de razonamiento activan
            # una fase de pensamiento que aqui solo suma segundos. La tarea es
            # resumir datos que ya vienen calculados, no deducirlos.
            "thinkingConfig": {"thinkingBudget": 0},
        },
    }

    try:
        with httpx.Client(timeout=TIEMPO_LIMITE) as cliente:
            for espera in (*ESPERAS, None):
                respuesta = cliente.post(
                    URL.format(modelo=GEMINI_MODEL),
                    # En cabecera y no como ?key=: la URL viaja en los mensajes
                    # de error de httpx y acabaria en los logs.
                    headers={"x-goog-api-key": GEMINI_API_KEY},
                    json=cuerpo,
                )
                if respuesta.status_code not in REINTENTABLES or espera is None:
                    break
                time.sleep(espera)

            respuesta.raise_for_status()
            texto = respuesta.json()["candidates"][0]["content"]["parts"][0]["text"]
            return json.loads(texto)
    except httpx.HTTPError as error:
        raise IANoDisponible(
            f"No se pudo consultar el modelo: {sin_clave(str(error))}"
        ) from error
    except (KeyError, IndexError, ValueError) as error:
        raise IANoDisponible(
            f"El modelo respondio algo que no se pudo leer: {sin_clave(str(error))}"
        ) from error
