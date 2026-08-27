# Ferretería Salinas — recomendaciones por sucursal

Prueba técnica full-stack. **POC funcional**: cinco sucursales, un inventario
compartido y un sistema que propone qué más ofrecerle al cliente en el mostrador.

> **La idea de fondo: la tienda importa tanto como el producto.** El mismo
> tornillo no es la respuesta correcta en Cancún y en Chihuahua, y un sistema que
> solo mira qué se vendió junto nunca puede saberlo.

**¿Vienes a probarlo?** Salta a [Puesta en marcha](#3-puesta-en-marcha): dos
terminales, unos cinco minutos, y no hace falta ninguna clave de API.

---

## Índice

| | |
|---|---|
| [1. El negocio](#1-el-negocio) | Qué es, qué se pedía, qué dicen los datos |
| [2. Tecnologías](#2-tecnologías-y-versiones) | Stack exacto y por qué |
| [3. Puesta en marcha](#3-puesta-en-marcha) | Cómo levantarlo y qué probar |
| [4. Arquitectura](#4-arquitectura) | Sistema, capas y patrones |
| [5. Backend](#5-backend) | Cómo está hecho y qué se prueba |
| [6. Recomendador](#6-el-recomendador) | Cómo decide y qué tan bien acierta |
| [7. Frontend](#7-frontend) | Las tres pantallas |
| [8. API REST](#8-api-rest) | Las decisiones del contrato |
| [9. La IA](#9-la-ia-opcional) | Qué hace el modelo y qué no |
| [10. Qué se complicó](#10-qué-se-complicó-y-cómo-se-resolvió) | Los problemas reales |
| [11. Qué falta](#11-qué-falta) | Siguientes pasos |

Este README explica **qué se construyó y por qué**. El detalle vive en:

| Documento | Qué contiene |
|---|---|
| **[`docs/api.md`](docs/api.md)** | Las 17 rutas una por una: parámetros, ejemplos y errores |
| **[`docs/decisiones.md`](docs/decisiones.md)** | Registro de decisiones, con las alternativas descartadas |
| **[`docs/evaluacion.md`](docs/evaluacion.md)** | Salida completa del script de evaluación |

---

## 1. El negocio

Una ferretería con **cinco sucursales que comparten un solo inventario**. El
usuario no compra por internet: es el **vendedor de mostrador con un cliente
delante**. Eso decide el resto — pantallas densas, teclado antes que ratón, nada
de marketing.

Las sucursales no son iguales:

| Sucursal | Condiciones | Qué implica |
|---|---|---|
| CDMX | Interior urbano | Basta material estándar |
| Cancún · Mérida | Costero salino | El aire salino se come el acero al carbón |
| Chihuahua | Sol directo, seco | El PVC común se cristaliza a la intemperie |
| Monterrey | Taller metalmecánico | Cliente de obra, consumibles de soldadura |

### El objetivo

> **Subir las ventas con un sistema de recomendaciones.**

No «hacer un recomendador». Subir las ventas. La diferencia importa: el éxito se
mide en tickets más grandes, no en métricas de laboratorio.

### Qué pedía la prueba

| Requisito | Dónde está |
|---|---|
| CRUD de productos | [§5](#5-backend) · pantalla de Catálogo |
| Compra que descuenta inventario **sin sobrevender** | [§5](#lo-más-importante-no-sobrevender) |
| Recomendaciones de complemento y sustituto | [§6](#6-el-recomendador) |
| Que funcione sin historial (sucursal o producto nuevos) | [§6](#los-dos-casos-sin-historial) |
| Panel para que el negocio ajuste las sugerencias | [§7](#relaciones) |
| Evaluación con baselines | [§6](#qué-tan-bien-acierta) |
| Uso opcional de un LLM | [§9](#9-la-ia-opcional) |

### Qué dicen los datos

Los CSV se revisaron antes de escribir código. **Esto es lo que condicionó toda
la arquitectura:**

| Hecho | Consecuencia |
|---|---|
| 28 productos, 89 líneas de venta, **42 tickets** | Muestra pequeña: las correlaciones son ruido |
| 45 pares se compran juntos, **solo 8 en más de un ticket** | Las reglas de asociación no pueden ser el motor |
| Todos los tickets tienen ≥2 artículos | Se puede evaluar con leave-one-out |
| **Mérida no aparece en `sales.csv`** | Una sucursal entera sin historial |
| **SKU027** (regulador MAPP) sin una sola venta | Un producto sin historial |

Con 42 tickets, mirar solo el histórico cubre lo que ya se vendió junto y nada
más: ni Mérida, ni SKU027, ni el resto del catálogo. Por eso el motor es la
**capa de atributos** (familia del producto × ambiente de uso), y las reglas de
asociación son **la evidencia**, no el motor.

### Qué se entregó

API con 17 operaciones, tres pantallas, **84 pruebas automatizadas** y evaluación
offline reproducible. Los ocho criterios de aceptación, verificados:

- [x] `pytest` pasa, incluido el test de concurrencia con **50 hilos**
- [x] Ninguna recomendación trae `stock = 0` ni `activo = 0`
- [x] **Mérida** devuelve recomendaciones coherentes con su clima
- [x] **SKU027** sale como complemento del soplete pese a no tener ventas
- [x] Bloquear una relación la saca del mostrador **sin reiniciar nada**
- [x] Agotar un SKU lo saca del catálogo comprable **y** de las recomendaciones
- [x] `evaluar.py` imprime números reales contra cuatro baselines
- [x] Sin dependencias fuera de las declaradas

---

## 2. Tecnologías y versiones

| Capa | Elección | Por qué |
|---|---|---|
| API | **FastAPI 0.141.1** · Python 3.13.3 | Validación y documentación salen del mismo tipado |
| Datos | **SQLite** con `sqlite3` de la stdlib, **sin ORM** | Lo crítico es controlar la transacción exacta; un ORM mete sesiones y threading sin aportar nada aquí |
| Validación | **Pydantic 2.13.4** | Los límites se declaran una vez y valen para entrada, salida y `/docs` |
| HTTP saliente | **httpx 0.28.1** | Única salida a internet: la llamada al modelo |
| Interfaz | **Next 16.3.3** · React 19.2.8 · TypeScript 5.9.3 | App Router, todo en cliente |
| Estilos | **Tailwind 4.3.3** | Tokens con `@theme`; el color de acento cambia con la sucursal |
| Datos de servidor | **TanStack Query 5.102.6** | Refrescar tras cobrar es funcional, no estético |
| Iconos | **lucide-react 1.34.0** | Sin fotos de producto (ver [§7](#por-qué-no-hay-fotos)) |

Completan la lista **uvicorn 0.52.4**, **pytest 9.1.1** y **Node 22.15.0**.

**Nada fuera de esta lista.** Sin ORM, sin Redux ni Zustand, sin react-router,
sin librería de notificaciones, sin API de imágenes.

---

## 3. Puesta en marcha

Necesitas **Python 3.11+** y **Node 20+**. Son dos procesos, así que hacen falta
dos terminales.

### Terminal 1 — API, queda ocupada en `http://localhost:8000`

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate            # Windows.  macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt

python -m app.seed                       # carga los CSV
python scripts/construir_relaciones.py   # calcula las sugerencias
uvicorn app.main:app --reload
```

> `uvicorn` tiene que correr **dentro de `backend/`**. Desde la raíz falla con
> `ModuleNotFoundError: No module named 'app'`, porque el paquete `app/` está ahí
> dentro.

Al arrancar, la API deja en la consola lo que encontró:

```
  Ferreteria Salinas - API 0.1.0
  Base de datos : ...\backend\ferreteria.db
  Contenido     : 28 productos activos - 5 sucursales - 42 tickets - 151 relaciones
  Frontend      : http://localhost:3000
  Comprobalo en : http://localhost:8000/  o  /docs
```

Si la base está vacía, el mismo mensaje lo dice y muestra los comandos que
faltan.

### Terminal 2 — Interfaz, queda ocupada en `http://localhost:3000`

```bash
cd frontend
npm install
npm run dev
```

Abre **http://localhost:3000**. La API tiene una portada de estado en
**http://localhost:8000/** y documentación interactiva en **/docs**.

### Variables de entorno

Ninguna es obligatoria. Los `.env.example` son plantillas: cópialos solo si
quieres cambiar algo.

| Archivo | Variable | Por defecto |
|---|---|---|
| `backend/.env` | `DB_PATH` · `CORS_ORIGINS` | `ferreteria.db` · `http://localhost:3000` |
| `backend/.env` | `GEMINI_API_KEY` · `GEMINI_MODEL` | vacío — solo activa el análisis con IA |
| `frontend/.env.local` | `NEXT_PUBLIC_API_URL` | `http://localhost:8000` |

**Sin clave de IA el sistema funciona completo.** Es lo único que la necesita.

### Qué probar primero

1. **Mostrador** — busca «soplete». Fíjate en las dos secciones de sugerencias y
   en que cada una dice de dónde sale. Agrega al ticket y cobra: el stock baja.
2. **Cambia a Cancún o Mérida** con el mismo producto: las sugerencias cambian
   porque cambia el clima.
3. **Catálogo en Mérida** — abajo aparece lo que el sistema detecta que le falta
   a esa sucursal, que es justo la que no tiene ventas en los datos.
4. **Relaciones** — bloquea una relación y vuelve al Mostrador: ya no aparece,
   sin reiniciar nada.

### Comprobar que funciona

```bash
cd backend
pytest -v                    # 84 pruebas, incluidas 50 hilos contra stock 8
python scripts/evaluar.py    # evaluación contra 4 baselines
```

---

## 4. Arquitectura

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
backend. Con eso dado, la interfaz es otro proceso: servirla desde FastAPI
obligaría a usar plantillas y a renunciar a React justo en la pantalla con más
estado local, el ticket en curso. La frontera es HTTP con CORS explícito y **un
solo cliente** en `lib/api.ts` — ningún componente hace `fetch` por su cuenta.

| Alternativa | Por qué no |
|---|---|
| **Next full-stack**, sin FastAPI | El enunciado fija Python. Y se pierde el control fino de la transacción SQLite, que es lo crítico |
| **Renderizado en servidor** consumiendo FastAPI | Duplica el modelo de datos en TypeScript y en Pydantic, a cambio de un SEO que un sistema interno no necesita |
| **Next como proxy** de FastAPI | Un salto de red más y otro sitio donde traducir errores. Ambos corren en localhost y no hay secretos que ocultar |

También se descartaron un monolito con Jinja —descarta React, que el enunciado
pide— y los microservicios, que son infraestructura para un problema que no
existe con 28 productos.

**Los scripts están fuera del ciclo de petición a propósito.** Sembrar, calcular
reglas, evaluar 89 pliegues o llamar a un LLM son procesos por lotes. Nada de eso
debe pasar mientras un vendedor espera con un cliente delante.

### Del código

```
backend/app/
├── routers/         HTTP → servicios. Nunca abren transacciones
├── services/        Lógica de negocio y LÍMITE TRANSACCIONAL
├── repositories/    Todo el SQL. Los servicios no conocen SQLite
├── schemas/         Contratos de entrada y salida (Pydantic)
├── ia/              Única salida a internet: cliente + analista
└── recomendador/
    ├── base.py       Protocol FuenteRecomendacion + Candidato
    ├── historico.py  Pares que se venden juntos + Wilson
    ├── perfiles.py   Clima de la sucursal × ambiente del producto
    ├── atributos.py  Familias y roles (conocimiento del negocio)
    └── ranking.py    Mezcla + filtros duros

frontend/
├── app/             layout + 3 vistas (Mostrador, Catálogo, Relaciones)
├── lib/             api.ts (único cliente HTTP), contextos, avisos
├── hooks/           uno por recurso
└── componentes/     presentación pura, sin fetch
```

**Capas y no hexagonal.** Ports & adapters sirve cuando hay que poder sustituir
la infraestructura; aquí la base es SQLite por requisito y no va a cambiar.
Habría añadido interfaces y contenedores sin comprar nada.

### Los cuatro patrones, y dónde

| Patrón | Dónde | Qué aporta |
|---|---|---|
| **Repository** | `repositories/*.py` | Todo el SQL en un sitio, con nombres de negocio (`descontar_stock`). Esa función **es** la garantía de no sobreventa y tiene que leerse de un vistazo |
| **Service Layer** | `services/*.py` | Es dueño del **límite transaccional**. Un router nunca abre una transacción, así que no hay dos sitios que puedan hacer `commit` de lo mismo |
| **Strategy** | `recomendador/` | `FuenteRecomendacion` es un `Protocol`, no una clase base: una fuente nueva es una clase suelta que no hereda de nada. Lo aprovecha `evaluar.py`, que inyecta una fuente en memoria en cada pliegue |
| **Inyección de dependencias** | `Depends(obtener_bd)` | Una conexión por petición, cerrada siempre en `finally`. Permite que los tests apunten a una base temporal sin tocar el código |

**Los servicios no importan FastAPI.** Lanzan excepciones de dominio y un
`exception_handler` central las traduce a códigos HTTP. Por eso el test de
concurrencia llama a `compra_service` directamente, sin levantar el servidor.

---

## 5. Backend

### Lo más importante: no sobrevender

La comprobación va **dentro del `UPDATE`**, no en un `SELECT` previo:

```python
cur.execute("BEGIN IMMEDIATE")
...
cur.execute("""UPDATE productos SET stock = stock - ?
                WHERE sku = ? AND activo = 1 AND stock >= ?""", (n, sku, n))
if cur.rowcount != 1:
    raise StockInsuficiente(sku)      # aborta el ticket entero
```

Entre un `SELECT` y un `UPDATE` cabe otra venta. Aquí no hay hueco: la condición
y la escritura son la misma operación atómica.

- `BEGIN IMMEDIATE` toma el candado de escritura al abrir, no en el primer
  `UPDATE`.
- `CHECK (stock >= 0)` en el esquema, por si algún día alguien escribe mal otro
  `UPDATE`.
- `PRAGMA journal_mode=WAL`, `foreign_keys=ON`, `busy_timeout=5000`.
- **Endpoints `def`, nunca `async def`**: `sqlite3` bloquea, y con `async def`
  bloquearía el event loop. El test de concurrencia dejaría de medir lo que dice.

**Idempotencia.** `Idempotency-Key` en cabecera. La clave se reserva con un
`INSERT` contra una PRIMARY KEY dentro de la misma transacción, así que tampoco
hay hueco entre comprobar y reservar. Un doble clic devuelve el ticket original
con `repetida: true` y no descuenta nada.

### Modelo de datos

| Decisión | Por qué |
|---|---|
| `movimientos_inventario` solo inserta, nunca borra | Queda por qué el stock vale lo que vale. Una devolución no borra: inserta un movimiento positivo |
| Borrado **lógico** de productos | `ventas` y `movimientos` apuntan al SKU; borrarlo rompería el historial |
| `UNIQUE(sku_origen, sku_destino, tipo)` en `relaciones` | Una fila por par. Si las dos fuentes proponen el mismo, gana el histórico porque trae evidencia |
| `estado` y `peso_manual` separados del `score` | El score lo calcula la máquina y se recalcula; el ajuste lo pone una persona y **sobrevive a recalcular** |
| `tiendas.id` sin acentos, `nombre` con acento | `sales.csv` trae `Cancún`; meter acentos en ids y URLs da problemas de encoding |
| `analisis_ia` con **huella del estado** | Permite devolver el análisis guardado sin volver a llamar al modelo |

### Validación de entrada

Los límites se declaran **una vez** como tipos reutilizables y valen igual en el
alta y en la edición. Duplicarlos era la forma segura de que un día el `PATCH`
aceptara lo que el `POST` rechaza. El SKU viaja en la URL y se normaliza a
mayúsculas; los textos tienen tope y no admiten caracteres de control, que es lo
que llega al pegar desde Excel. El frontend repite los límites para avisar
mientras escribes, pero **el backend sigue siendo la autoridad**.

Campo por campo, en [`docs/api.md`](docs/api.md).

### Pruebas

**84 pruebas** que corren contra una base sembrada desde cero en una carpeta
temporal. Cubren la compra (que sea todo o nada, e idempotente), el CRUD completo
por servicio y por HTTP, el contrato que consume el frontend, los filtros del
recomendador, los tres modos, los avisos de sucursal y la caché de la IA.

La que más importa es `test_concurrencia.py`: **50 hilos contra stock 8**. Pasan
exactamente 8, el stock acaba en 0 y los movimientos cuadran. Se usa base en
disco y no `:memory:` a propósito, porque necesita varias conexiones reales sobre
el mismo archivo — que es lo que ejercita WAL y `BEGIN IMMEDIATE`.

---

## 6. El recomendador

### Dos fuentes, una mezcla

**Histórico** — pares que ya se vendieron juntos. Se puntúan con el **límite
inferior de Wilson** en vez de la frecuencia bruta: penaliza las muestras
pequeñas, que con 42 tickets son casi todas.

**Atributos** — conocimiento del negocio **escrito a mano** en `atributos.py`:
qué familias existen y qué rol complementa a cuál. No lo deduce nadie; lo pondría
un jefe de piso, y por eso está todo junto y comentado para que el negocio pueda
discutirlo sin leer el resto del código.

| | Sustituto | Complemento |
|---|---|---|
| **Qué es** | Misma familia, mejor material para la sucursal | Misma actividad, rol distinto |
| **Ejemplo** | Tornillo de carbón → inoxidable 316 en Cancún | Soplete → cartucho de gas |
| **Regla** | Depende del clima de la sucursal | **Nunca** de la misma familia |

### Los dos casos sin historial

- **Mérida** (cero tickets): ninguna regla de asociación puede hablar de esa
  sucursal. Su clima sí, porque no depende del histórico sino de los atributos
  del producto.
- **SKU027** (cero ventas): entra como complemento del soplete porque la tabla de
  atributos dice que un regulador acompaña a un soplete, no porque alguien los
  haya comprado juntos.

Las relaciones por atributos se guardan **sin sucursal**; el ajuste a cada plaza
se hace al servir. Así Mérida funciona sin historial y el sustituto correcto
cambia por sucursal sin duplicar filas.

### Filtros duros, no penalizaciones

Antes de devolver se quita lo que tenga `stock = 0`, `activo = 0`, esté ya en el
ticket o esté bloqueado. **No baja de puntaje: desaparece.** Un producto sin
existencia no es una mala sugerencia, es imposible. Vive en un solo sitio
—`ranking.mezclar`— para que haya un solo punto que auditar.

### Los tres modos del panel

El negocio no elige «histórico 1.0 / atributos 0.65». Elige **cuánta evidencia
exige**:

| Modo | hit-rate@3 | Sugerencias por producto |
|---|---:|---:|
| Solo lo comprobado | 0.326 | 2.2 |
| **Equilibrado** (día a día) | **0.472** | 3.4 |
| Descubrir más | 0.494 | 4.5 |

Exigir más evidencia **cuesta aciertos, y está bien que los cueste**: se recorta
la cola de sugerencias deducidas y ahí caía alguno. Es preferir precisión antes
que cobertura, a sabiendas.

### Qué tan bien acierta

Leave-one-out sobre los 42 tickets, 89 casos, **sin hacer trampa**: las reglas se
recalculan ocultando el ticket que se está midiendo.

| Recomendador | hit-rate@3 | IC 95% (Wilson) | MRR |
|---|---:|:---:|---:|
| **híbrido (este sistema)** | **0.472** | [0.372, 0.575] | **0.330** |
| más vendido en la tienda | 0.337 | [0.247, 0.440] | 0.180 |
| misma categoría | 0.135 | [0.079, 0.221] | 0.096 |
| aleatorio con stock | 0.112 | [0.062, 0.195] | 0.071 |
| más vendido global | 0.112 | [0.062, 0.195] | 0.052 |

**El intervalo es ancho y se solapa.** Con 42 tickets no da para declarar un
ganador con significancia estadística, y decir lo contrario sería vender ruido
como resultado.

**El número que más dice del proyecto:** sobre **7 pares que tienen sentido pero
nunca aparecen juntos** en `sales.csv`, el histórico acierta **0/7** —no puede
contar lo que nunca pasó— y los atributos **6/7**. Ahí se ve por qué los
atributos son el motor y el histórico la evidencia.

Detalle completo en [`docs/evaluacion.md`](docs/evaluacion.md).

---

## 7. Frontend

Tres pantallas, un solo usuario en mente.

### Mostrador

Buscar → revisar sugerencias → cobrar. Abre con un saludo, la sucursal y los tres
pasos: **nadie debería necesitar el README para usar la pantalla**. Mientras no
hay producto elegido, unas herramientas en gris ocupan el hueco en vez de dejar
la pantalla vacía.

- `/` enfoca el buscador, las flechas navegan, `Enter` elige, `Ctrl+Enter` cobra.
  El vendedor viene de escribir y no debería soltar el teclado.
- Las secciones se llaman **«Mejor para esta plaza»** y **«Para terminar el
  trabajo»**, no «Recomendados»: así se sabe para qué sirve cada una.
- Cada sugerencia muestra **de dónde sale** («8 tickets» / «por atributos»).
- **El ticket sobrevive al cambio de pestaña.** Vive en el layout, que no se
  desmonta entre rutas. Solo se vacía al cambiar de sucursal, porque un ticket
  pertenece a la plaza donde se cobra.

### Catálogo

CRUD con edición sobre la propia fila: el encargado corrige precios de varios
productos seguidos, y un modal por cada uno multiplica los clics sin aportar
nada.

Debajo, los **avisos** de la sucursal activa: qué no se ha vendido nunca, qué se
vende en otras plazas y aquí no, qué se agotó, qué material no aguanta el clima.
Se calculan en el backend, se pueden ocultar y cada uno trae **qué hacer** — un
diagnóstico sin acción no sirve de nada.

### Relaciones

Lo que el sistema sabe sugerir, en lenguaje de negocio. La primera versión
mostraba `soporte`, `confianza`, `lift` y `score` en columnas: es exactamente lo
que el sistema calcula, y **era ilegible para quien tiene que decidir**. Ahora
cada fila dice de dónde sale y qué tan fuerte es, y se ajusta con cuatro opciones
con nombre —*normal*, *preferir*, *siempre*, *nunca*— en vez de un número.

Arriba, el análisis con IA ([§9](#9-la-ia-opcional)); abajo, los tres modos.

### Decisiones que afectan a todo

**Solo dos cosas son globales**, la sucursal y el ticket, porque son las dos que
se comparten entre rutas. Lo demás viene del servidor (TanStack Query) o es local
a una vista. **Sin Redux ni Zustand**: un store sería una segunda copia de datos
que ya están en la caché de Query, con el riesgo de que no coincidan.

**Refrescar tras cobrar es funcional, no estético.** Sin invalidar productos y
recomendaciones, la interfaz mostraría el stock anterior y **podría ofrecer un
producto recién agotado**, rompiendo un requisito desde el frontend.

**Un solo cliente HTTP** (`lib/api.ts`); ningún componente hace `fetch`. Si el
manejo de errores estuviera repartido, el mensaje «Quedan 3» dependería de quién
escribió cada llamada.

### Por qué no hay fotos

Cada producto es un icono por categoría, un color por ambiente y el SKU. **El
color codifica el ambiente**, que es el eje sobre el que el sistema propone
sustitutos. Una foto genérica que no corresponde al material enseñaría al
vendedor a ignorar justo la diferencia que importa.

---

## 8. API REST

17 operaciones. Cada una existe porque algo la llama: quince las usa la interfaz
y dos son para el operador (`GET /` y `GET /api/salud`).

| Decisión | Por qué |
|---|---|
| `PATCH` y no `PUT` para productos | La edición del catálogo es parcial. Un `PUT` obligaría a mandar el producto entero y a arriesgar pisar campos |
| `PUT` y no `PATCH` para los pesos | Al revés: son tres números que solo significan algo juntos |
| `DELETE` → `204`, borrado lógico y repetible | Repetirlo no falla: el efecto ya se cumplió |
| `Idempotency-Key` en **cabecera** | Es información de transporte, no parte del ticket |
| La recomendación es `GET` | Es una lectura: tiene que ser repetible y cacheable |
| El error de stock lleva `sku` y `disponible` | El mostrador necesita el número, no un texto que tendría que parsear |
| Sin versionado ni paginación | No hay consumidor externo al que romperle nada, y son 28 productos |

**El parámetro `tienda` no filtra el inventario**, que es el mismo en las cinco:
ordena el catálogo y cambia qué se recomienda.

Cada ruta con sus parámetros, ejemplos y errores está en
**[`docs/api.md`](docs/api.md)**, incluido qué significa el `additionalProp1` que
Swagger muestra en los ejemplos.

---

## 9. La IA (opcional)

Sin `GEMINI_API_KEY` todo lo demás funciona igual.

### Qué hace: analiza, no recomienda

```
POST /api/analisis  {"tienda": "merida"}     ← botón en la pantalla de Relaciones
```

Una sola llamada con el retrato de una sucursal —catálogo con existencias y
ventas, dinero parado en inventario, peso dentro de la cadena, las relaciones del
recomendador y los avisos ya detectados— que devuelve **una lectura del negocio y
del propio sistema**, con las decisiones que tocan.

El retrato lleva **las cuentas ya hechas**. Un modelo sumando columnas se
equivoca y no hay forma de saberlo; explicando una suma que ya viene calculada,
no. Así la pregunta es «qué significa este 12 %» y no «cuánto suma esta columna».

### Por qué no redacta

La primera versión usaba el LLM para reescribir las justificaciones una a una:
**151 llamadas** para cambiar *cómo suena* algo que el sistema ya sabía. Ahora es
**una sola**, solo si el sistema cambió, y produce información que el sistema no
tenía. Si falla, no hay análisis y nada más se ve afectado.

### Cómo se evita gastar cuota

Antes de preguntar se calcula una **huella** del estado: catálogo, precios,
existencias, ventas por sucursal, relaciones, bloqueos y pesos. Si coincide con
la del último análisis guardado, se devuelve ese sin tocar la red.

| | Tiempo | ¿Consulta al modelo? |
|---|---:|---|
| Primera llamada | 3–5 s | sí |
| Segunda, sin cambios | 0.3 s | **no** |
| Tras cambiar un precio | — | el botón se reactiva |
| Al revertir ese precio | — | misma huella: reutiliza el análisis |

**La garantía está en el servidor, no en el botón**, así no depende de que el
cliente se acuerde de comprobarlo.

### Qué modelo y por qué

`gemini-3.1-flash-lite`, elegido **por cuota, no por capacidad**: en el plan
gratuito el flash puntero da 5 peticiones por minuto y 20 al día, y este 15 y
500. Se desactiva la fase de razonamiento y se acota la salida, porque la
latencia la marca el texto que el modelo **escribe**, no el que lee.

Con cinco sucursales facturando, la restricción deja de ser la cuota y pasa a ser
la calidad de la lectura:

| Escenario | Modelo | Por qué |
|---|---|---|
| Análisis mensual por sucursal | **Gemini 3 Pro** o equivalente de gama alta | Son 5 llamadas al mes: el coste da igual y razona mucho mejor sobre inventario y temporadas |
| Análisis diario o bajo demanda | Flash puntero, sin la variante *lite* | Equilibrio entre latencia y profundidad |
| Volumen alto | El actual, con contexto cacheado | El retrato del catálogo apenas cambia entre llamadas |

Con más datos aparece un uso que hoy no tiene sentido: **detectar temporadas y
anticipar la demanda por sucursal**. Con 42 tickets, un modelo que hable de
tendencias estaría inventando, y el prompt se lo prohíbe.

### Qué no hace

**No decide qué se recomienda ni en qué orden.** El ranking sigue siendo
determinista y evaluable offline; meter un LLM en el camino rompería las dos
cosas y añadiría latencia de red a la pantalla de alguien que tiene un cliente
delante.

Su respuesta se **recorta antes de guardarse** —máximo cuatro puntos por sección,
textos acotados— para que un texto de 4000 caracteres no rompa la pantalla del
encargado. Sin clave responde `503`, no `500`: el sistema está bien, lo que falta
es un servicio externo y opcional.

---

## 10. Qué se complicó y cómo se resolvió

**Los tres modos del panel no cambiaban nada.** Al medirlos, de 140 consultas
(28 productos × 5 sucursales) los tres devolvían **las mismas sugerencias**; solo
cambiaba el orden. La causa: un peso multiplica el puntaje, y como casi ningún
producto tiene más de seis candidatos, el tope nunca recortaba. Un peso responde
«cuál prefiero»; el negocio pregunta «cuánta evidencia exijo», que es **un corte,
no un multiplicador**. Se derivó de los pesos que ya existían y relativo al mejor
candidato, para que Mérida no se quede en blanco. Ahora cambia en 110 de 140, y
`test_modos.py` lo fija.

**La lista de pares de prueba hacía trampa.** Daba al histórico 18/20 porque los
pares los había elegido mirando los datos. Se rehízo con 7 pares que nunca
aparecen juntos y el histórico cayó a **0/7**. Ese cero es el argumento del
proyecto; el 18/20 no medía nada.

**El sistema se contradecía.** Proponía cambiar un tornillo por el inoxidable
**y** llevarse además el galvanizado: misma familia, o sea alternativas entre sí.
El histórico lo reintroducía porque alguien los compró juntos una vez. Se
resolvió moviendo la exclusión a `ranking.mezclar`, sobre **todas** las fuentes.

**Una justificación que no se sostenía.** Para Mérida proponía CPVC anti-UV
diciendo «resiste radiación solar directa» y a la vez «aquí el aire salino se
come el acero común». Se cambió por una comparación entre el ambiente del
producto y el de la sucursal. Una justificación que no se sostiene es peor que
ninguna: el vendedor la repite al cliente y queda mal.

**Un `500` donde tocaba un `422`.** Auditando las 17 operaciones —48 casos entre
respuestas correctas y errores— un peso negativo pasaba la validación y reventaba
contra el `CHECK` de la base. Un `500` ahí es mentir: el dato es inválido, no el
servidor. En la misma auditoría, `GET /api/productos` era la única ruta que
aceptaba una sucursal inexistente y respondía `200`.

**La clave en los mensajes de error.** `httpx` mete la URL completa en el texto
de sus excepciones, así que el primer 404 imprimió la API key en consola. Se
movió a la cabecera `x-goog-api-key` y se añadió una función que la sustituye en
cualquier mensaje antes de que llegue a un log o a una respuesta.

**El ticket se perdía al consultar un precio.** Vivía dentro de la vista del
Mostrador, y con enrutado por ficheros esa vista se desmonta al ir a Catálogo. Se
movió a un contexto colgado del layout.

---

## 11. Qué falta

**Lo primero: saber cuántas sugerencias se aceptan.** Hoy no se registra si una
línea entró al ticket desde una sugerencia ni de qué fuente. Sin eso no se puede
responder «¿está subiendo las ventas?», que es la pregunta del cliente. Todo lo
demás va después.

**Módulo de tickets.** Se cobra y el inventario baja, pero el ticket se pierde al
recargar y no queda comprobante. Los datos ya están en `ventas` agrupados por
`ticket_id`: falta exponerlos y una vista con filtros. Las devoluciones ya están
previstas — `movimientos_inventario` solo inserta, así que una devolución no
borra nada, mete un movimiento positivo.

**Los datos de Mérida.** Lo que no se hizo, a propósito: **inventar ventas**.
Habría sido fácil generar tickets copiando Cancún y todas las métricas habrían
mejorado, pero eso contamina la evaluación con datos que nadie observó y esconde
el problema interesante, que es demostrar que el sistema responde sin historial.
Lo que sí se hizo: que el sistema lo diga, con un aviso al entrar en Mérida. En
producción tocaría dar de alta la sucursal declarando su clima, prestarle las
reglas de la vecina con el mismo clima marcadas como *«prestado de Cancún»*, y
quitarles peso conforme acumule tickets propios.

| Otras ideas | Qué costaría |
|---|---|
| **Lector de código de barras** | Casi nada: el buscador ya acepta SKU, y un lector es un teclado que escribe y pulsa Enter |
| **`familia` como columna del maestro** | Hoy es una constante: un producto nuevo no entra en ninguna familia hasta tocar código |
| **Autenticación y roles** | Relaciones y el CRUD no pueden estar abiertos. OAuth2 con roles `vendedor` / `encargado` |
| **Aviso de reabastecimiento** | Ya se lista lo agotado; falta que avise solo y calcule cuándo pedir |
| **Sugerencias por temporada** | Una clase nueva que cumpla `FuenteRecomendacion`: justo el caso para el que se eligió Strategy |
| **A/B en mostrador** | La única forma de demostrar que las recomendaciones suben ventas. Necesita antes la tasa de aceptación |

**Sobre Next y Vite.** Se entregó con Next porque el enunciado lo lista, pero
**este sistema no necesita nada de lo que Next aporta**: es una herramienta
interna tras autenticación, sin SEO ni contenido que prerenderizar. Vite habría
dado un build más simple y un despliegue estático, sin proceso Node en
producción. Lo que Next sí aportó —enrutado por ficheros y `next/font`— es
cómodo, no imprescindible.

**Fuera de alcance en esta POC:** autenticación, varios almacenes de verdad,
precios por sucursal, devoluciones, impresión de tickets y despliegue. Están
descritos, no implementados: hacerlos a medias habría restado tiempo a lo que la
prueba sí evalúa.
