# Ferretería Salinas — recomendaciones por sucursal

Prueba técnica full-stack. **POC funcional**: cinco sucursales, un inventario
compartido y un sistema que propone qué más ofrecerle al cliente en el mostrador.

> **La tesis del proyecto: el contexto de la tienda importa tanto como el
> producto.** El mismo tornillo no es la respuesta correcta en Cancún y en
> Chihuahua, y un sistema que solo mira qué se vendió junto nunca puede saberlo.

---

## Índice

| | |
|---|---|
| [1. El negocio](#1-el-negocio) | Qué es, qué se pedía, qué dicen los datos |
| [2. Qué se entregó](#2-qué-se-entregó) | Resultado y criterios cumplidos |
| [3. Tecnologías](#3-tecnologías-y-versiones) | Stack exacto y por qué |
| [4. Puesta en marcha](#4-puesta-en-marcha) | Pasos para levantarlo |
| [5. Arquitectura](#5-arquitectura) | Sistema, capas, patrones |
| [6. Backend](#6-backend) | Desarrollo y pruebas |
| [7. Recomendador](#7-el-recomendador) | Cómo decide y qué tan bien |
| [8. Frontend](#8-frontend) | Las tres pantallas |
| [9. API REST](#9-api-rest) | Diseño del contrato |
| [10. Capa de IA](#10-capa-de-ia) | Qué hace el modelo y qué no |
| [11. Qué se complicó](#11-qué-se-complicó-y-cómo-se-resolvió) | Los problemas reales |
| [12. Qué falta](#12-qué-falta) | Siguientes pasos |

Documentos de apoyo: **[`docs/api.md`](docs/api.md)** (la API ruta por ruta),
**[`docs/decisiones.md`](docs/decisiones.md)** (registro de decisiones),
**[`docs/evaluacion.md`](docs/evaluacion.md)** (reporte generado por el script
de evaluación).

---

## 1. El negocio

### Qué es

Una ferretería con **cinco sucursales que comparten un solo inventario**. El
usuario no es un comprador online: es el **vendedor de mostrador con un cliente
enfrente**. Eso decide todo lo demás — densidad alta, teclado antes que ratón,
cero marketing.

Las plazas no son intercambiables:

| Sucursal | Condiciones | Qué implica |
|---|---|---|
| CDMX | Interior urbano | Basta material estándar; el sobrecosto no se justifica |
| Cancún · Mérida | Costero salino | El aire salino se come el acero al carbón |
| Chihuahua | Sol directo, seco | El PVC común se cristaliza a la intemperie |
| Monterrey | Taller metalmecánico | Cliente de obra, consumibles de soldadura |

### El objetivo

> **Subir las ventas con un sistema de recomendaciones.**

No «hacer un recomendador». Subir las ventas. La diferencia importa: mide el
éxito en tickets más grandes, no en métricas de laboratorio.

### Qué pedía la prueba

| Requisito | Dónde está |
|---|---|
| CRUD de productos | [§6](#6-backend) · pantalla de Catálogo |
| Compra que descuenta inventario **sin sobrevender** | [§6](#el-requisito-bloqueante-no-sobrevender) |
| Recomendaciones de complemento y sustituto | [§7](#7-el-recomendador) |
| Que funcione con cold start (plaza y producto sin historia) | [§7](#los-dos-arranques-en-frío) |
| Panel para que el negocio ajuste las sugerencias | [§8](#relaciones) |
| Evaluación con baselines | [§7](#qué-tan-bien-funciona) |
| Uso opcional de un LLM | [§10](#10-capa-de-ia) |

### Qué dicen los datos (antes de escribir código)

Los CSV se revisaron primero. **Esto es lo que condicionó toda la arquitectura:**

| Hecho | Consecuencia de diseño |
|---|---|
| 28 productos, 89 líneas de venta, **42 tickets** | Muestra pequeña: el lift es ruido estadístico |
| 45 pares co-ocurren, **solo 8 en más de un ticket** | Las reglas de asociación no pueden ser el motor |
| Todas las canastas tienen ≥2 artículos | Leave-one-out aplicable a las 42 |
| **Mérida no aparece en `sales.csv`** | Arranque en frío de sucursal completo |
| **SKU027** (regulador MAPP) sin una sola venta | Arranque en frío de producto |

**Conclusión:** con 42 tickets, un histórico puro cubre lo que ya se vendió
junto y nada más — ni Mérida, ni SKU027, ni el resto del catálogo. Por eso el
motor es la **capa de atributos** (familia funcional × ambiente de uso), y las
reglas de asociación son **la evidencia auditable**, no el motor.

Ese análisis previo es la razón de que el sistema esté construido como está, y
no al revés.

---

## 2. Qué se entregó

Un sistema operativo de punta a punta: API con 17 operaciones, tres pantallas,
**84 pruebas automatizadas** y evaluación offline reproducible.

**Los ocho criterios de aceptación, verificados:**

- [x] `pytest` pasa, incluido el test de concurrencia con **50 hilos**
- [x] Ninguna recomendación trae `stock = 0` ni `activo = 0`
- [x] **Mérida** devuelve recomendaciones coherentes con perfil costero
- [x] **SKU027** aparece como complemento del soplete pese a no tener ventas
- [x] Bloquear una relación la saca del mostrador **sin reiniciar nada**
- [x] Agotar un SKU lo saca del catálogo comprable **y** de las recomendaciones
- [x] `evaluar.py` imprime números reales contra cuatro baselines
- [x] Sin dependencias fuera de las declaradas

---

## 3. Tecnologías y versiones

| Capa | Elección | Por qué |
|---|---|---|
| API | **FastAPI 0.141.1** · Python 3.13.3 | Validación y documentación salen del mismo tipado |
| Datos | **SQLite** con `sqlite3` de la stdlib, **sin ORM** | El requisito crítico es controlar la transacción exacta; un ORM mete sesiones y threading sin aportar nada |
| Validación | **Pydantic 2.13.4** | Los límites se declaran una vez y valen para entrada, salida y `/docs` |
| Servidor | **uvicorn 0.52.4** | — |
| HTTP saliente | **httpx 0.28.1** | Única salida a Internet: la llamada al modelo |
| Pruebas | **pytest 9.1.1** | — |
| Interfaz | **Next 16.3.3** · React 19.2.8 · TypeScript 5.9.3 | App Router, todo cliente |
| Estilos | **Tailwind 4.3.3** | Tokens con `@theme`; el acento cambia con la sucursal |
| Estado de servidor | **TanStack Query 5.102.6** | La invalidación tras cobrar es funcional, no cosmética |
| Iconos | **lucide-react 1.34.0** | Sin fotos de producto (ver [§8](#por-qué-no-hay-fotos)) |
| Runtime | Node 22.15.0 | — |

**Cero dependencias fuera de esta lista.** Sin ORM, sin Redux ni Zustand, sin
react-router, sin librería de notificaciones, sin API de imágenes.

---

## 4. Puesta en marcha

Requisitos: **Python 3.11+** y **Node 20+**. Son dos procesos y hacen falta dos
terminales.

### Terminal 1 — API (queda ocupada en `http://localhost:8000`)

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate            # Windows.  macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt

python -m app.seed                       # carga los CSV
python scripts/construir_relaciones.py   # materializa las sugerencias
uvicorn app.main:app --reload
```

> `uvicorn` debe correr **dentro de `backend/`**. Desde la raíz falla con
> `ModuleNotFoundError: No module named 'app'`, porque el paquete `app/` vive
> ahí dentro.

El seed imprime `28 productos | 89 lineas de venta en 42 tickets | 5 tiendas`, y
el arranque deja en la consola qué encontró:

```
  Ferreteria Salinas - API 0.1.0
  Base de datos : ...\backend\ferreteria.db
  Contenido     : 28 productos activos - 5 sucursales - 42 tickets - 151 relaciones
  Frontend      : http://localhost:3000
  Comprobalo en : http://localhost:8000/  o  /docs
```

Si la base no está sembrada, el mismo banner lo dice y muestra los comandos que
faltan.

### Terminal 2 — Interfaz (queda ocupada en `http://localhost:3000`)

```bash
cd frontend
npm install
npm run dev
```

Abre **http://localhost:3000**. La API tiene portada de estado en
**http://localhost:8000/** y documentación interactiva en **/docs**.

### Variables de entorno

Los `.env.example` son plantillas: cópialos y rellena si hace falta.

| Archivo | Variable | Obligatoria |
|---|---|---|
| `backend/.env` | `DB_PATH`, `CORS_ORIGINS` | No, hay valores por defecto |
| `backend/.env` | `GEMINI_API_KEY`, `GEMINI_MODEL` | **No.** Solo activa el análisis con IA |
| `frontend/.env.local` | `NEXT_PUBLIC_API_URL` | No, por defecto `http://localhost:8000` |

**Sin clave de IA el sistema funciona completo.** Es lo único que la necesita.

### Comprobar que funciona

```bash
cd backend
pytest -v                    # 84 pruebas, incluidas 50 hilos contra stock 8
python scripts/evaluar.py    # evaluación contra 4 baselines
```

---

## 5. Arquitectura

### Del sistema

```
┌────────────────────────┐      HTTP/JSON      ┌────────────────────────────┐
│  Next 16      :3000    │  ────────────────▶  │  FastAPI       :8000       │
│  navegador             │  ◀────────────────  │  uvicorn + threadpool      │
│                        │   CORS explícito    └─────┬──────────────────┬───┘
│  TanStack Query        │                           │ sqlite3          │ httpx
│  = caché del estado    │                           ▼                  ▼
│    que vive en el      │                 ┌──────────────────┐  ┌────────────┐
│    servidor            │                 │ SQLite (WAL)     │  │  Gemini    │
└────────────────────────┘                 │ ferreteria.db    │  │  opcional  │
                                           └────────▲─────────┘  └────────────┘
       fuera del ciclo de petición ─────────────────┘
       seed · construir_relaciones · evaluar · redactar_justificaciones
```

**Por qué dos procesos y no uno.** El enunciado fija Python + FastAPI para el
backend. Con eso dado, la interfaz es necesariamente otro proceso: servirla
desde FastAPI habría obligado a plantillas y a renunciar al modelo de
componentes justo en la pantalla con más estado local del sistema, el ticket en
curso. La frontera es HTTP con CORS explícito y **un único cliente** en
`lib/api.ts` — ningún componente hace `fetch` por su cuenta.

| Alternativa | Por qué no |
|---|---|
| **Next full-stack** (route handlers, sin FastAPI) | El enunciado fija Python. Y perdería el control fino de la transacción SQLite, que es el requisito crítico |
| **Renderizado en servidor consumiendo FastAPI** | Dobla el modelo de datos —TypeScript y Pydantic— y obliga a decidir en cada vista qué se renderiza dónde, a cambio de un SEO que un sistema interno no necesita |
| **Next como BFF** (proxy `/api/*` → FastAPI) | Un salto de red más y un segundo sitio donde traducir errores, a cambio de nada: ambos corren en localhost y no hay secretos que ocultar al navegador |
| **Monolito con Jinja** | Descarta React, que el enunciado pide, y complica el mostrador |
| **Microservicios** | Infraestructura para un problema que no existe con 28 productos |

**Los scripts están fuera del ciclo de petición a propósito.** Sembrar,
construir reglas, evaluar 89 pliegues o llamar a un LLM son procesos por lotes.
Nada de eso debe ocurrir mientras un vendedor espera con un cliente enfrente.

### Del código

```
backend/app/
├── routers/         HTTP → servicios. Nunca abren transacciones
├── services/        Lógica de negocio y LÍMITE TRANSACCIONAL
├── repositories/    Todo el SQL. Los servicios no conocen SQLite
├── schemas/         Contratos de entrada y salida (Pydantic)
├── ia/              Única salida a Internet: cliente + analista
└── recomendador/
    ├── base.py       Protocol FuenteRecomendacion + Candidato
    ├── historico.py  Co-ocurrencia + Wilson
    ├── perfiles.py   Perfil de plaza × ambiente del producto
    ├── atributos.py  Familias y roles (conocimiento de dominio declarado)
    └── ranking.py    Mezcla + filtros duros

frontend/
├── app/             layout + 3 vistas (Mostrador, Catálogo, Relaciones)
├── lib/             api.ts (único cliente HTTP), contextos, notificaciones
├── hooks/           uno por recurso
└── componentes/     presentación pura, sin fetch
```

**Capas y no hexagonal.** Ports & adapters tiene sentido cuando hay que
sustituir una infraestructura; aquí la base es SQLite por requisito y no va a
cambiar. Habría añadido interfaces y contenedores sin comprar nada que no dé ya
la separación por capas.

### Los cuatro patrones, y dónde exactamente

| Patrón | Dónde | Qué compra |
|---|---|---|
| **Repository** | `repositories/*.py` | Todo el SQL en un sitio. Métodos con nombre de negocio (`descontar_stock`), no genéricos: esa función **es** la garantía de no sobreventa y tiene que poder leerse de un vistazo |
| **Service Layer** | `services/*.py` | Es dueño del **límite transaccional**. Un router nunca abre una transacción, así que no hay dos sitios que puedan hacer `commit` de lo mismo |
| **Strategy** | `recomendador/` | `FuenteRecomendacion` es un `Protocol`, no una clase base: una fuente nueva —temporada, promociones— es una clase suelta que no hereda de nada. Lo aprovecha `evaluar.py`, que inyecta una fuente en memoria por pliegue |
| **Inyección de dependencias** | `Depends(obtener_bd)` | Una conexión por petición, cerrada siempre en `finally`. Es lo que permite que los tests apunten a una base temporal sin tocar el código |

**Dónde sí se invierte la dependencia:** solo en `ranking.mezclar`, que recibe
las fuentes y el predicado de familia por parámetro. No conoce ninguna fuente
concreta, y por eso el mismo código sirve al mostrador y a la evaluación.

**Los servicios no importan FastAPI.** Lanzan excepciones de dominio; un
`exception_handler` central las traduce a códigos HTTP. Por eso el test de
concurrencia llama a `compra_service` directamente, sin levantar el servidor.

---

## 6. Backend

### El requisito bloqueante: no sobrevender

La comprobación vive **dentro del `UPDATE`**, no en un `SELECT` previo:

```python
cur.execute("BEGIN IMMEDIATE")
...
cur.execute("""UPDATE productos SET stock = stock - ?
                WHERE sku = ? AND activo = 1 AND stock >= ?""", (n, sku, n))
if cur.rowcount != 1:
    raise StockInsuficiente(sku)      # aborta el ticket entero
```

Entre un `SELECT` y un `UPDATE` cabe otra venta. Aquí no hay ventana: la
condición y la escritura son la misma operación atómica.

- `BEGIN IMMEDIATE` toma el candado de escritura al abrir, no en el primer
  `UPDATE`.
- `CHECK (stock >= 0)` en el esquema como última defensa ante un `UPDATE` mal
  escrito en el futuro.
- `PRAGMA journal_mode=WAL`, `foreign_keys=ON`, `busy_timeout=5000`.
- **Endpoints `def` y nunca `async def`**: `sqlite3` es bloqueante y con
  `async def` bloquearía el event loop, con lo que el test de concurrencia
  dejaría de medir lo que dice medir.

**Idempotencia.** `Idempotency-Key` en cabecera. La clave se reserva con un
`INSERT` contra una PRIMARY KEY dentro de la misma transacción: no hay ventana
entre comprobar y reservar porque son la misma operación. Un doble clic devuelve
el ticket original con `repetida: true` y no descuenta nada.

### Modelo de datos

| Decisión | Por qué |
|---|---|
| `movimientos_inventario` **append-only** | Auditoría de por qué el stock vale lo que vale. Una devolución no borra: inserta un delta positivo |
| Borrado **lógico** de productos | `ventas` y `movimientos` referencian el SKU; borrarlo rompería el historial |
| `UNIQUE(sku_origen, sku_destino, tipo)` en `relaciones` | Una fila por par. Si ambas fuentes proponen el mismo, gana el histórico porque lleva evidencia |
| `estado` y `peso_manual` separados del `score` | El score lo calcula la máquina y se recalcula; el ajuste lo pone una persona y **sobrevive a reconstruir las reglas** |
| `tiendas.id` slug ASCII, `nombre` con acento | `sales.csv` trae `Cancún`; arrastrar acentos a ids y URLs es una fuente segura de bugs de encoding |
| `analisis_ia` con **huella del estado** | Permite devolver el análisis guardado sin volver a llamar al modelo |

### Validación de entrada

Los límites se declaran **una vez** como tipos reutilizables y valen igual en el
alta y en la edición; duplicarlos era la vía segura para que un día el `PATCH`
aceptara lo que el `POST` rechaza.

| Regla | Motivo |
|---|---|
| SKU `^[A-Za-z0-9][A-Za-z0-9_-]{1,23}$`, a mayúsculas | Viaja en la URL. `sku001` y `SKU001` no pueden ser dos productos |
| Nombre 2–120 · categoría 2–40 · uso ≤80 · descripción ≤300 | Margen sobre los 44 caracteres del CSV, sin permitir pegar un PDF |
| Precio ≤ 9 999 999 · stock ≤ 1 000 000 | Sin tope cabe `1e308`, que rompe cualquier suma posterior |
| Sin caracteres de control | Llegan al pegar desde Excel: descuadran tablas y hacen que dos productos idénticos parezcan distintos |

El frontend replica los límites para avisar al escribir; **el backend sigue
siendo la autoridad** y valida igual.

### Pruebas

```
84 pruebas · pytest
```

| Archivo | Qué cubre |
|---|---|
| `test_concurrencia.py` | **50 hilos contra stock 8**: pasan exactamente 8, stock final 0, y el libro de movimientos cuadra |
| `test_compra.py` | Atomicidad del ticket, idempotencia, casos límite |
| `test_crud.py` · `test_crud_api.py` | CRUD por servicio y **ciclo completo por HTTP**: alta → edición → baja → reactivación → venta |
| `test_contrato_api.py` | El contrato que consume el frontend: código de estado de 36 rutas y forma exacta del JSON |
| `test_recomendaciones.py` | Filtros duros, cold start, bloquear/fijar/peso |
| `test_modos.py` | Que los tres modos del panel **cambien qué se ofrece**, no solo el orden |
| `test_diagnostico.py` | Que los hallazgos salgan de los datos y desaparezcan solos al cambiar |
| `test_analisis.py` | Que la IA no consulte dos veces por lo mismo y que su respuesta se sanee |

Cada test corre contra una base sembrada desde cero en un directorio temporal. Se
usa base en disco y no `:memory:` a propósito: el test de concurrencia necesita
varias conexiones reales sobre el mismo archivo, que es lo que ejercita WAL y
`BEGIN IMMEDIATE`.

---

## 7. El recomendador

### Dos fuentes, una mezcla

**Histórico** — pares que ya se vendieron juntos. Se puntúan con el **límite
inferior de Wilson**, no con la frecuencia bruta: penaliza las muestras
pequeñas, que con 42 tickets son casi todas.

**Atributos** — conocimiento de dominio **declarado explícitamente** en
`atributos.py`: familias funcionales y qué rol complementa a cuál. No es
inferencia; lo pondría un jefe de piso, y por eso está junto y comentado para
que el negocio pueda discutirlo sin leer el resto del código.

| | Sustituto | Complemento |
|---|---|---|
| **Qué es** | Misma familia, mejor material para la plaza | Misma actividad, rol distinto |
| **Ejemplo** | Tornillo de carbón → inoxidable 316 en Cancún | Soplete → cartucho de gas |
| **Regla** | Depende del perfil de la sucursal | **Nunca** de la misma familia |

### Los dos arranques en frío

- **Mérida** (cero tickets): ninguna regla de asociación puede hablar de esa
  plaza. Su perfil sí, porque no depende del histórico sino de los atributos del
  producto.
- **SKU027** (cero ventas): entra como complemento del soplete porque la tabla
  de dominio dice que un regulador acompaña a un soplete, no porque alguien los
  haya comprado juntos.

Las relaciones por atributos se guardan **sin dimensión de tienda**; la
adecuación a la plaza se resuelve al servir. Así Mérida funciona sin historial y
el sustituto correcto cambia por sucursal sin duplicar filas.

### Filtros duros, no ponderaciones

Antes de devolver se elimina lo que tenga `stock = 0`, `activo = 0`, esté en el
ticket o esté bloqueado. **No es una penalización de puntaje**: un producto sin
existencia no es una mala sugerencia, es una imposible. Vive en un solo punto
—`ranking.mezclar`— para que haya un solo sitio que auditar.

### Los tres modos del panel

El negocio no elige «histórico 1.0 / atributos 0.65». Elige **cuánta evidencia
exige**:

| Modo | hit-rate@3 | Sugerencias por producto |
|---|---:|---:|
| Solo lo comprobado | 0.326 | 2.2 |
| **Equilibrado** (día a día) | **0.472** | 3.4 |
| Descubrir más | 0.494 | 4.5 |

Exigir más evidencia **cuesta aciertos, y es correcto que los cueste**: se
recorta la cola de sugerencias deducidas y ahí caía alguno. Es precisión antes
que cobertura, tomada a conciencia.

### Qué tan bien funciona

Leave-one-out sobre las 42 canastas, 89 instancias, **sin fuga de datos** (las
reglas se reconstruyen ocultando el ticket que se mide):

| Recomendador | hit-rate@3 | IC 95% (Wilson) | MRR |
|---|---:|:---:|---:|
| **híbrido (este sistema)** | **0.472** | [0.372, 0.575] | **0.330** |
| más vendido en la tienda | 0.337 | [0.247, 0.440] | 0.180 |
| misma categoría | 0.135 | [0.079, 0.221] | 0.096 |
| aleatorio con stock | 0.112 | [0.062, 0.195] | 0.071 |
| más vendido global | 0.112 | [0.062, 0.195] | 0.052 |

**El intervalo es ancho y se solapa.** Con 42 canastas no da para declarar un
ganador estadísticamente significativo, y presentarlo como si diera sería
presentar ruido como métrica.

**La cifra que más dice del proyecto:** sobre **7 pares de dominio que nunca
co-ocurren** en `sales.csv`, el histórico recupera **0/7** —imposible por
construcción, no puede contar lo que nunca pasó— y los atributos **6/7**. Ahí se
ve por qué los atributos son el motor y el histórico la evidencia.

Detalle completo en **[`docs/evaluacion.md`](docs/evaluacion.md)**.

---

## 8. Frontend

Tres pantallas, un solo usuario en mente.

### Mostrador

Buscar → revisar sugerencias → cobrar. Abre con un saludo, la sucursal y los
tres pasos: **nadie debería necesitar el README para usar la pantalla**. Mientras
no hay producto elegido, un estado de espera en gris ocupa el hueco en vez de
dejar medio metro de fondo vacío.

- `/` enfoca el buscador, flechas navegan, `Enter` elige, `Ctrl+Enter` cobra. El
  vendedor viene de escribir y no debería soltar el teclado.
- Etiquetas **«Mejor para esta plaza»** y **«Para terminar el trabajo»**, nunca
  «Recomendados»: dicen para qué sirve cada bloque.
- Cada sugerencia muestra **de dónde sale** («8 tickets» / «por atributos»). El
  vendedor tiene derecho a saber si se apoya en ventas o en criterio.
- **El ticket sobrevive al cambio de pestaña.** Vive en el layout, que no se
  desmonta entre rutas; solo se vacía al cambiar de sucursal —ahí sí: un ticket
  pertenece a la plaza donde se cobra— y cuando pasa, lo dice.

### Catálogo

CRUD completo con edición en línea sobre la propia fila: el encargado corrige
precios de varios productos seguidos, y un modal por cada uno multiplica los
clics sin aportar nada.

Debajo, una banda de **mejoras detectadas** para la sucursal activa: qué no se ha
vendido nunca, qué se vende en otras plazas y aquí no, qué se agotó, qué material
no aguanta el clima de la zona. Se calcula en el backend, se puede ocultar, y
cada hallazgo trae **qué hacer** — un diagnóstico sin acción solo genera
ansiedad.

### Relaciones

El catálogo auditable de lo que el sistema sabe sugerir, en lenguaje de negocio.
La primera versión mostraba `soporte`, `confianza`, `lift`, `score` y
`peso_manual` en columnas numéricas: es exactamente lo que el sistema calcula, y
**era ilegible para quien tiene que decidir**. Ahora cada fila dice de dónde sale
y qué tan fuerte es, y se ajusta con cuatro opciones con nombre —*normal*,
*preferir*, *siempre*, *nunca*— en vez de escribir un número.

Arriba, el análisis con IA ([§10](#10-capa-de-ia)); abajo, los tres modos.

### Decisiones transversales

**Estado.** Solo dos cosas son globales —la sucursal y el ticket— y lo son por la
misma razón: se comparten entre rutas. Lo demás o es de servidor (TanStack Query)
o es local a una vista. **Sin Redux ni Zustand**: un store añadiría una segunda
copia de datos que ya están en la caché de Query, con el riesgo clásico de que
discrepen. Dos contextos de ~150 líneas no justifican una dependencia.

**La invalidación es funcional, no cosmética.** Tras cobrar se invalidan
productos, recomendaciones y diagnóstico. Sin eso la interfaz mostraría el stock
anterior y **podría ofrecer un producto recién agotado**, rompiendo un requisito
bloqueante desde el frontend.

**Un único cliente HTTP** (`lib/api.ts`). Si el manejo de errores viviera
repartido, el mensaje «Quedan 3» dependería de quién escribió cada llamada.

**Toda acción que cambia datos deja constancia.** Avisos hechos a mano (~60
líneas, sin librería) con `aria-live` para no robar el foco mientras se escribe.

**La aplicación ocupa la ventana, no la página.** `body` es un flex de `100dvh`;
las tres columnas del mostrador llegan exactamente hasta abajo y cada una decide
qué scrollea dentro.

**Profundidad contenida.** Dos alturas de sombra y no cinco: una superficie está
apoyada o está levantada. Una escala más larga solo produce discusiones sobre
cuál toca en cada sitio.

### Por qué no hay fotos

Cada producto es un icono por categoría + chip de color por ambiente + SKU en
monoespaciada. **El color del chip codifica el ambiente**, que es justo el eje
sobre el que el sistema propone sustitutos. Una foto genérica que no corresponde
al material contradice la tesis del proyecto y enseña al vendedor a ignorar la
diferencia que importa.

---

## 9. API REST

17 operaciones. Cada una existe porque algo concreto la llama: quince las consume
la interfaz y dos son para el operador (`GET /` y `GET /api/salud`).

| Decisión | Por qué |
|---|---|
| `PATCH` y no `PUT` para productos | La edición del catálogo es parcial. Un `PUT` obligaría a mandar el recurso completo y a arriesgar pisar campos |
| `PUT` y no `PATCH` para los pesos | Al revés: son tres números que solo significan algo juntos |
| `DELETE` → `204`, borrado lógico e **idempotente** | Repetirlo no falla: el efecto buscado ya se cumplió |
| `Idempotency-Key` en **cabecera** | Es metadato de transporte, no parte del ticket |
| `excluir=SKU,SKU` como query param | La recomendación es una lectura: tiene que ser `GET`, repetible y cacheable |
| El error de stock lleva `sku` y `disponible` | El mostrador necesita el número, no un texto que tendría que parsear |
| Sin versionado ni paginación | No hay consumidor externo al que romperle nada, y son 28 productos. Sería ceremonia |

**El parámetro `tienda` no filtra el inventario**, que es el mismo en las cinco:
ordena el catálogo y cambia qué se recomienda.

**Referencia completa —cada ruta, sus parámetros, ejemplos reales de petición y
respuesta y todos sus errores— en [`docs/api.md`](docs/api.md)**, incluido qué
significa el `additionalProp1` que Swagger muestra en los ejemplos.

---

## 10. Capa de IA

**Opcional.** Sin `GEMINI_API_KEY` todo lo demás funciona igual.

### Qué hace: analiza, no recomienda

```
POST /api/analisis  {"tienda": "merida"}     ← botón en la pantalla de Relaciones
```

Una sola llamada con el retrato completo de una plaza —catálogo con existencias y
ventas, valor inmovilizado, participación en la cadena, concentración, las
relaciones del recomendador y los hallazgos que el diagnóstico ya detectó— y
devuelve **una lectura del negocio y del propio sistema**, con las decisiones que
tocan.

El retrato lleva **las cuentas hechas**. Un modelo sumando columnas se equivoca y
no hay forma de saberlo; un modelo explicando una suma que ya viene calculada,
no. Eso convierte la pregunta en analítica —«qué significa este 12 %»— en vez de
aritmética.

### Por qué no redacta

La primera versión usaba el LLM para reescribir las justificaciones una a una.
Funcionaba, pero costaba **una llamada por relación** para cambiar *cómo suena*
algo que el sistema ya sabía.

| | Redactar (antes) | Analizar (ahora) |
|---|---|---|
| Llamadas | 151 | **1**, y solo si el sistema cambió |
| Qué produce | la misma información, mejor escrita | información que el sistema **no** tenía |
| Si falla | queda el texto de plantilla | no hay análisis; nada más se ve afectado |

### Cómo se evita gastar cuota

Antes de preguntar se calcula la **huella** del estado: catálogo, precios,
existencias, ventas por plaza, relaciones, bloqueos y pesos. Si coincide con la
del último análisis guardado, se devuelve ese sin tocar la red.

| | Tiempo | ¿Consulta al modelo? |
|---|---:|---|
| Primera llamada | 3–5 s | sí |
| Segunda, sin cambios | 0.3 s | **no** |
| Tras cambiar un precio | — | el botón se reactiva |
| Al revertir ese precio | — | misma huella: reutiliza el análisis |

**La garantía vive en el servidor, no en el botón**, así no depende de que ningún
cliente se acuerde de comprobarlo.

### Qué modelo y por qué

`gemini-3.1-flash-lite`, elegido **por cuota, no por capacidad**. En el tier
gratuito el flash puntero da 5 peticiones por minuto y 20 al día; este da 15 y
500. Se fija la versión a conciencia: el coste es que caduca —`gemini-2.0-flash`
ya devuelve 404— y por eso el fallo se degrada en lugar de romper.

Se desactiva la fase de razonamiento (`thinkingBudget: 0`) y se acota la salida:
la latencia la manda el texto que el modelo **escribe**, no el que lee.

**Qué modelo usaría con el negocio real.** Con cinco sucursales facturando, la
restricción deja de ser la cuota gratuita y pasa a ser la calidad de la lectura:

| Escenario | Modelo | Por qué |
|---|---|---|
| Análisis mensual por sucursal | **Gemini 3 Pro** o equivalente de gama alta | Son 5 llamadas al mes: el coste es irrelevante y el razonamiento sobre inventario y estacionalidad mejora mucho |
| Análisis diario o bajo demanda | Flash puntero, sin la variante *lite* | Equilibrio entre latencia y profundidad |
| Volumen alto | El actual, con contexto cacheado | El retrato del catálogo apenas cambia entre llamadas |

Con más datos aparece un uso que hoy no tiene sentido: **detectar estacionalidad
y anticipar la demanda por plaza**. Con 42 tickets, un modelo que hable de
tendencias estaría inventando — y el prompt se lo prohíbe explícitamente.

### Qué no hace

**No decide qué se recomienda ni en qué orden.** El ranking sigue siendo
determinista y evaluable offline; meter un LLM en el camino de servir rompería
las dos cosas y añadiría latencia de red a la pantalla de alguien que tiene un
cliente enfrente.

Lo que devuelve se **recorta antes de guardarse**: máximo cuatro puntos por
sección, textos acotados, un `impacto` inventado cae a `medio`, y un punto sin
análisis o sin acción se descarta. Un texto de 4000 caracteres no puede romper la
pantalla del encargado ni quedar guardado como si fuera válido.

Sin clave responde `503`, no `500`: el sistema está bien, lo que falta es un
servicio externo y opcional.

---

## 11. Qué se complicó y cómo se resolvió

### Los tres modos del panel no cambiaban nada

Al medirlos: de **140 consultas** (28 productos × 5 plazas), los tres devolvían
**el mismo conjunto** de sugerencias. Solo cambiaba el orden.

La causa: un peso **multiplica el puntaje**, y como casi ningún producto tiene
más de seis candidatos, el tope nunca recorta. Un peso responde «cuál prefiero»;
el negocio pregunta «cuánta evidencia exijo», que es **un corte, no un
multiplicador**. Se derivó de los pesos existentes —sin configuración nueva— y
relativo al mejor candidato, para que Mérida no se quede en blanco. Ahora cambia
el conjunto en 110 de 140, y `test_modos.py` lo fija.

### El conjunto dorado hacía trampa

La primera versión daba al histórico 18/20 — porque los pares los había elegido
mirando los datos. Se rehízo con **7 pares verificados que nunca co-ocurren**, y
el histórico cayó a **0/7**. Ese cero es el argumento del proyecto; el 18/20 no
medía nada.

### El sistema se contradecía a sí mismo

Proponía cambiar un tornillo por el inoxidable **y** llevarse también el
galvanizado: dos productos de la misma familia, que son alternativas. El
histórico lo reintroducía porque alguien los compró juntos una vez. Se resolvió
moviendo la exclusión a `ranking.mezclar`, sobre **todas** las fuentes, en vez de
dentro de una sola.

### Una justificación que no se sostenía

Para Mérida el sistema proponía CPVC anti-UV diciendo «resiste radiación solar
directa» y, a la vez, «aquí el aire salino se come el acero común». Una frase
fija por perfil se contradecía con la ventaja real del sustituto. Se cambió por
una comparación entre el ambiente del producto actual y el de la plaza. Una
justificación que no se sostiene es peor que ninguna: el vendedor la repite al
cliente y queda mal.

### Un `500` donde tocaba un `422`

Auditando las 17 operaciones —48 casos entre respuestas correctas y errores—
apareció que un peso negativo pasaba la validación y reventaba contra el `CHECK`
de la base. Un `500` ahí es mentir: el dato es inválido, no el servidor. En la
misma auditoría, `GET /api/productos` era la única ruta que aceptaba una sucursal
inexistente y respondía `200` con el orden alfabético.

### La credencial en los mensajes de error

`httpx` incluye la URL completa en el texto de sus excepciones, así que el primer
404 imprimió la API key en consola. Se movió a cabecera `x-goog-api-key` y se
añadió un saneador que la sustituye en cualquier mensaje antes de que llegue a un
log o a una respuesta HTTP.

### El ticket se perdía al consultar un precio

Vivía dentro de la vista del Mostrador, y con enrutado por ficheros esa vista se
desmonta al ir a Catálogo. Se movió a un contexto colgado del layout, que no se
desmonta entre rutas.

---

## 12. Qué falta

### Lo primero que añadiría

**Tasa de aceptación de la sugerencia.** Hoy no se registra si una línea entró al
ticket *desde una sugerencia* y de qué fuente. Sin eso no se puede responder
«¿está subiendo las ventas?», que es literalmente la pregunta del cliente. Todo
lo demás va después.

### Módulo de tickets

Se cobra y el inventario baja, pero el ticket se pierde al recargar y no queda
comprobante. Los datos ya están en `ventas` agrupados por `ticket_id`: falta
exponerlos y una vista con filtro por fecha y sucursal. Las devoluciones ya están
preparadas por diseño — `movimientos_inventario` es append-only, así que una
devolución **no borra nada**, inserta un delta positivo.

### Los datos de Mérida

**Lo que no se hizo, a propósito: inventar ventas.** Habría sido fácil generar
tickets sintéticos copiando Cancún y todas las métricas habrían mejorado.
Contamina la evaluación con datos que nadie observó y **esconde el problema
interesante**, que es demostrar que el sistema responde sin historial.

Lo que sí se hizo: que el sistema lo diga. El diagnóstico lo detecta y el
Catálogo lo muestra al entrar en Mérida. Un sistema que no sabe algo debería
decirlo, no disimularlo.

En producción: onboarding de sucursal (el encargado declara el perfil de la
plaza), préstamo de reglas del vecino con el mismo perfil marcado como *«prestado
de Cancún»*, y decaimiento automático conforme acumule tickets propios.

### Otras

| Idea | Qué costaría |
|---|---|
| **Lector de código de barras** | Casi nada: el buscador ya acepta SKU, y un lector es un teclado que escribe y pulsa Enter |
| **`familia` como columna del maestro** | Hoy es una constante: un alta nueva no entra en ninguna familia hasta tocar código |
| **Autenticación y roles** | El panel de Relaciones y el CRUD no pueden estar abiertos. OAuth2 con scopes `vendedor` / `encargado` |
| **Reabastecimiento que se adelanta** | El diagnóstico ya lista lo agotado; falta que avise solo y calcule el punto de pedido |
| **Sugerencias por temporada** | Es **una clase nueva** que cumpla `FuenteRecomendacion`: justo el caso para el que se eligió Strategy |
| **A/B en mostrador** | La única forma de demostrar que las recomendaciones suben ventas. Requiere primero la tasa de aceptación |

### Sobre Next y Vite

Se entregó con Next porque el enunciado lo lista como stack. Conviene dejar por
escrito que **este sistema no necesita nada de lo que Next aporta**: es una
herramienta interna tras autenticación, sin SEO, sin enlaces que compartir, sin
contenido que prerenderizar. Vite habría dado un build más simple y un despliegue
de archivos estáticos, sin proceso Node en producción. Lo que Next sí aportó
aquí —enrutado por ficheros y `next/font`— es cómodo, no imprescindible.

### Fuera de alcance en esta POC

Autenticación · multi-almacén real (aquí el inventario es uno solo por
requisito) · precios por sucursal · devoluciones · impresión de tickets ·
despliegue. Están descritos, no implementados: hacerlos a medias habría restado
tiempo a lo que la prueba sí evalúa.
