"""Reescribe las justificaciones en lenguaje de mostrador con un LLM. OPCIONAL.

    python scripts/redactar_justificaciones.py

Sin GEMINI_API_KEY el script no hace nada y el sistema entero sigue funcionando
con el texto de plantilla. Es opcional de verdad, no opcional de mentira.

POR QUE EN BATCH Y NO EN LA API
-------------------------------
La tentacion es llamar al LLM dentro de GET /api/recomendaciones. Seria un
error por tres razones y las tres pesan mas que la comodidad:

1. Latencia. El usuario es un vendedor con un cliente enfrente. Meter una
   llamada de red en esa pantalla es empeorar justo lo que se quiere mejorar.
2. Arranque. Ataria la POC a que el evaluador tenga API key. Aqui no la
   necesita: sin clave ve el texto de plantilla y todo lo demas igual.
3. Determinismo. El ranking se evalua offline y tiene que dar el mismo numero
   dos veces. Un LLM en el camino de servir rompe eso.

El LLM NO decide que se recomienda ni en que orden. Solo redacta. El texto
queda en `justificacion_ia`, separado de la plantilla, visible y editable en el
panel de Relaciones: si escribe algo malo, el negocio lo ve y lo corrige.
"""

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx  # noqa: E402

from app.config import GEMINI_API_KEY, GEMINI_MODEL  # noqa: E402
from app.db import conectar  # noqa: E402
from app.repositories import relaciones_repo  # noqa: E402

URL = "https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent"
TAMANO_LOTE = 20
LARGO_MAXIMO = 180

# El tier gratuito devuelve 503 y 429 con frecuencia por saturacion. Son fallos
# transitorios, no errores de la peticion: sin reintento el script escribe una
# fraccion de lo que podria y parece roto cuando solo habia que esperar.
REINTENTABLES = (429, 500, 502, 503, 504)
ESPERAS = (2, 6, 15)

INSTRUCCION = """Eres el encargado de una ferreteria mexicana con 5 sucursales.
Reescribe cada justificacion para que un vendedor de mostrador se la pueda
repetir tal cual a un cliente que tiene enfrente.

Reglas estrictas:
- Maximo 140 caracteres. Una sola frase.
- Espanol de Mexico, tono directo y practico. Nada de marketing.
- No inventes datos, materiales ni cifras que no esten en la entrada.
- Si la entrada cita numero de tickets, puedes mencionarlo; si no, no lo cites.
- No uses signos de exclamacion.

Devuelve SOLO un arreglo JSON con la forma:
[{"id": <id>, "texto": "<justificacion reescrita>"}]

Relaciones a reescribir:
"""


def _sin_clave(error: Exception) -> str:
    """Nunca imprimir la credencial, venga de donde venga el mensaje."""
    texto = str(error)
    if GEMINI_API_KEY:
        texto = texto.replace(GEMINI_API_KEY, "***")
    return texto


def pedir_lote(cliente: httpx.Client, lote: list[dict]) -> dict[int, str]:
    entrada = [
        {
            "id": r["id"],
            "tipo": r["tipo"],
            "producto_ancla": r["nombre_origen"],
            "producto_sugerido": r["nombre_destino"],
            "justificacion_actual": r["justificacion"],
        }
        for r in lote
    ]
    cuerpo_peticion = {
        "contents": [
            {"parts": [{"text": INSTRUCCION + json.dumps(entrada, ensure_ascii=False)}]}
        ],
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0.4,
        },
    }

    for intento, espera in enumerate((*ESPERAS, None)):
        respuesta = cliente.post(
            URL.format(modelo=GEMINI_MODEL),
            # La clave va en cabecera y no como ?key=: httpx incluye la URL
            # completa en el texto de sus excepciones, asi que un 404 impreso
            # en consola filtraria la credencial a los logs.
            headers={"x-goog-api-key": GEMINI_API_KEY},
            json=cuerpo_peticion,
        )
        if respuesta.status_code not in REINTENTABLES or espera is None:
            break
        print(f"    {respuesta.status_code} transitorio, reintento en {espera}s")
        time.sleep(espera)

    respuesta.raise_for_status()
    cuerpo = respuesta.json()
    texto = cuerpo["candidates"][0]["content"]["parts"][0]["text"]

    salida = {}
    for item in json.loads(texto):
        redactado = str(item.get("texto", "")).strip()
        # El LLM puede devolver vacio, larguisimo o un id que no pedimos. Se
        # descarta en silencio y esa relacion se queda con su plantilla.
        if redactado and len(redactado) <= LARGO_MAXIMO:
            salida[int(item["id"])] = redactado
    return salida


def main() -> None:
    if not GEMINI_API_KEY:
        print(
            "GEMINI_API_KEY no esta definida: no se reescribe nada.\n"
            "El sistema funciona igual con las justificaciones de plantilla.\n"
            "Para activarlo, copia backend/.env.example a backend/.env y pon "
            "una clave gratuita de https://aistudio.google.com/apikey"
        )
        return

    bd = conectar()
    try:
        pendientes = [
            dict(r)
            for r in relaciones_repo.listar(bd)
            if not r["justificacion_ia"]
        ]
        if not pendientes:
            print("No hay relaciones pendientes de redactar.")
            return

        print(
            f"Redactando {len(pendientes)} justificaciones con {GEMINI_MODEL} "
            f"en lotes de {TAMANO_LOTE}..."
        )
        escritas = 0
        with httpx.Client(timeout=60.0) as cliente:
            for inicio in range(0, len(pendientes), TAMANO_LOTE):
                lote = pendientes[inicio : inicio + TAMANO_LOTE]
                try:
                    redactadas = pedir_lote(cliente, lote)
                except (httpx.HTTPError, KeyError, ValueError) as exc:
                    # Un lote fallido no puede tumbar el proceso ni dejar la
                    # base a medias: lo que ya se escribio es valido y lo que
                    # falta se queda con su plantilla.
                    print(f"  lote {inicio // TAMANO_LOTE + 1}: fallo ({_sin_clave(exc)})")
                    continue

                cur = bd.cursor()
                cur.execute("BEGIN IMMEDIATE")
                try:
                    for id_relacion, texto in redactadas.items():
                        relaciones_repo.guardar_justificacion_ia(bd, id_relacion, texto)
                    bd.commit()
                except Exception:
                    bd.rollback()
                    raise
                escritas += len(redactadas)
                print(
                    f"  lote {inicio // TAMANO_LOTE + 1}: "
                    f"{len(redactadas)}/{len(lote)} redactadas"
                )

        print(f"\nListo: {escritas} justificaciones reescritas.")
        if escritas < len(pendientes):
            print(
                f"{len(pendientes) - escritas} se quedaron con su plantilla, "
                "que es un texto valido."
            )
    finally:
        bd.close()


if __name__ == "__main__":
    main()
