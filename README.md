# Ferretería — inventario compartido y recomendaciones por plaza

POC para el área de innovación. Cinco tiendas (Cancún, Chihuahua, CDMX,
Monterrey, Mérida) sobre un **inventario compartido**, con un recomendador que
propone qué más llevar según el producto **y la plaza**.

El usuario no es un comprador online: es **el vendedor de mostrador con un
cliente esperando enfrente**. Toda la interfaz está diseñada para eso — densidad
alta, teclado antes que ratón, cero contenido de marketing.

---

## Levantar el proyecto en 4 comandos

Requisitos: **Python 3.13+** y **Node 20+**. No hace falta Docker ni API keys.

```bash
# 1. Backend: entorno, dependencias, base de datos y relaciones
cd backend && python -m venv .venv && .venv/Scripts/activate     # Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt && python -m app.seed && python scripts/construir_relaciones.py

# 2. Levantar la API  (http://localhost:8000/docs)
uvicorn app.main:app --reload

# 3. Frontend, en otra terminal
cd frontend && npm install && cp .env.example .env.local

# 4. Levantar la interfaz  (http://localhost:3000)
npm run dev
```

El seed debe imprimir:

```
28 productos  |  89 lineas de venta en 42 tickets  |  5 tiendas
```

### Variables de entorno

Ambos `.env.example` tienen valores por defecto que funcionan sin tocar nada.

| Archivo | Variable | Por defecto | Para qué |
|---|---|---|---|
| `backend/.env` | `DB_PATH` | `ferreteria.db` | Ruta de la base SQLite |
| `backend/.env` | `CORS_ORIGINS` | `http://localhost:3000` | Orígenes permitidos |
| `backend/.env` | `GEMINI_API_KEY` | *(vacío)* | **Opcional.** Sin clave todo funciona igual |
| `backend/.env` | `GEMINI_MODEL` | `gemini-3.1-flash-lite` | Elegido por cuota — ver abajo |
| `frontend/.env.local` | `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | URL de la API |

> Next exige el prefijo `NEXT_PUBLIC_` para exponer una variable al navegador.

---

## Qué mirar primero

| Vista | Qué demuestra |
|---|---|
| **Mostrador** (`/`) | Busca `soplete` → verás **SKU027 (regulador)** recomendado pese a **no tener ni una venta** |
| Cambia la tienda a **Mérida** | Busca `tornillo` → propone **inoxidable 316**, con **cero historial** en esa plaza. El acento de toda la UI cambia con la plaza y sale un aviso de qué cambia |
| **Relaciones** (`/relaciones`) | Abre *Soplete de gas MAPP* y pon una sugerencia en **No mostrar**. Vuelve al mostrador: **desapareció, sin reiniciar nada** |
| **Catálogo** (`/catalogo`) | Pon el stock de un producto en 0 → sale del mostrador y de las recomendaciones |

Atajo: `/` enfoca el buscador desde cualquier parte; flechas recorren y Enter
selecciona.

---

## Decisiones de interfaz

El usuario es **el vendedor de mostrador con un cliente enfrente**, no un
comprador online. Eso decide todo lo demás.

**El sistema se explica solo al entrar.** El Mostrador abre con un saludo, la
sucursal en la que estás y tres pasos (buscar → revisar sugerencias → cobrar).
Relaciones abre explicando qué es una sugerencia y de dónde sale. Nadie debería
necesitar el README para usar la pantalla.

**Toda acción que cambia datos deja constancia.** Avisos para agregar y quitar
del ticket, cobrar, crear, editar, dar de baja, reactivar, ajustar una sugerencia
y cambiar de sucursal. En un mostrador el vendedor no puede quedarse con la duda
de si el cobro entró. Están hechos a mano (~60 líneas, sin librería externa) y se
anuncian con `aria-live` para no robar el foco mientras se escribe.

**El cambio de sucursal avisa qué cambia**, no solo que cambió: *«Ahora se
priorizan materiales que aguantan el aire salino»*. El acento de toda la interfaz
cambia con la plaza — no es decoración, evita cobrar en la tienda equivocada.

**Animaciones cortas (130 ms) y solo donde informan**: hover de tarjeta y fila,
el botón se hunde al pulsarlo, los avisos entran y salen. Todo se desactiva con
`prefers-reduced-motion`: nadie debería marearse usando un punto de venta.

**Contención de texto.** Los nombres del catálogo llegan a 44 caracteres y las
justificaciones del LLM a 123. Hay utilidades `.recorta` / `.recorta-2` y
`min-w-0` en cada contenedor flex, más altura fija de dos líneas en las tarjetas
de sugerencia para que no queden desparejas.

### Relaciones: por qué ya no es una tabla de métricas

La primera versión mostraba `soporte`, `confianza`, `lift`, `score` y
`peso_manual` en columnas numéricas. Es exactamente lo que el sistema calcula —
y es **ilegible** para un encargado de tienda: nadie sabe si un lift de 9.3 es
bueno, ni qué hacer con un peso de 0.8.

El backend no cambió. Cambió cómo se presenta:

| Antes (lo que calcula el sistema) | Ahora (la decisión que toma el negocio) |
|---|---|
| 151 filas planas | Agrupadas por producto: *«si el cliente lleva X…»* |
| `fuente: historico` | **Lo dicen las ventas** — «se llevaron juntos en 2 tickets» |
| `fuente: atributos` | **Va con el producto** — mismo trabajo, pieza complementaria |
| `tipo: sustituto / complemento` | **«en lugar de»** / **«además de»** |
| `score: 0.607` | Barra de fuerza: Débil · Media · Fuerte · Muy fuerte |
| `estado` + `peso_manual` (dos campos) | **Un solo control de 4 opciones**: Siempre primero · Más seguido · Normal · No mostrar |
| `historico=1.0, atributos=0.8` | Tres modos: **Solo lo comprobado** · **Equilibrado** · **Descubrir más** |

Los números crudos siguen ahí: al pasar el ratón sobre la barra de fuerza, y en
«ver valores exactos» junto a los modos. El evaluador técnico los quiere ver; el
encargado no debería tropezarse con ellos.

Un detalle honesto: los sustitutos se guardan **sin puntaje** porque cuál conviene
depende de la plaza y eso se resuelve al servir. En vez de pintar una barra vacía
que parecería «muy débil», muestran **«Según la plaza»**.

---

## Comprobar que funciona

```bash
cd backend
pytest -v                    # 51 tests, incluye 50 hilos contra stock 8
python scripts/evaluar.py    # tabla real contra 4 baselines
```

| Archivo de tests | Qué cubre |
|---|---|
| `test_concurrencia.py` | 50 hilos contra stock 8; el libro de movimientos cuadra |
| `test_compra.py` | Atomicidad del ticket, idempotencia, casos límite |
| `test_crud.py` | CRUD a nivel de servicio y borrado lógico |
| `test_crud_api.py` | **Ciclo completo por HTTP**: alta → edición → baja → reactivación → venta, y el efecto de cada operación sobre lo que el mostrador puede vender y recomendar |
| `test_recomendaciones.py` | Filtros duros, cold start, bloquear/fijar/peso |

**Resultado de la evaluación** (leave-one-out sobre las 42 canastas, 89
instancias, sin fuga de datos):

| Recomendador | hit-rate@3 | IC 95% (Wilson) | MRR |
|---|---:|:---:|---:|
| **híbrido (este sistema)** | **0.506** | [0.404, 0.607] | **0.343** |
| más vendido en la tienda | 0.337 | [0.247, 0.440] | 0.180 |
| misma categoría | 0.135 | [0.079, 0.221] | 0.096 |
| aleatorio con stock | 0.112 | [0.062, 0.195] | 0.071 |
| más vendido global | 0.112 | [0.062, 0.195] | 0.052 |

**El intervalo es ancho y se solapa.** Con 42 canastas no da para declarar un
ganador estadísticamente significativo, y presentarlo como si diera sería
presentar ruido como métrica. Por eso la evaluación incluye dos comprobaciones
cualitativas más — detalle completo en **[`docs/evaluacion.md`](docs/evaluacion.md)**.

La que más dice del proyecto: sobre **7 pares de dominio que nunca co-ocurren**
en `sales.csv`, el histórico recupera **0/7** y los atributos **6/7**.

---

## Cómo funciona el recomendador

Dos fuentes que implementan el mismo `Protocol`, mezcladas por un ranking común.
Añadir una fuente es añadir una clase: ni el ranking ni la API se tocan.

```
                    ┌──────────────────────────┐
   producto + tienda│  recomendacion_service   │
        ────────────▶                          │
                    └────────────┬─────────────┘
                                 │
                 ┌───────────────┴───────────────┐
                 ▼                               ▼
    ┌────────────────────────┐     ┌────────────────────────┐
    │   HistoricoStrategy    │     │   AtributosStrategy    │
    │  co-ocurrencia real    │     │  familia × ambiente    │
    │  Wilson sobre soporte  │     │  actividad × rol       │
    │  → EVIDENCIA           │     │  → MOTOR               │
    └───────────┬────────────┘     └───────────┬────────────┘
                └───────────────┬───────────────┘
                                ▼
                    ┌──────────────────────────┐
                    │      ranking.mezclar     │
                    │  pesos + ajustes manuales│
                    │  FILTROS DUROS ← único   │
                    │  punto que garantiza que │
                    │  nada agotado se propone │
                    └────────────┬─────────────┘
                                 ▼
                   sustituto + complementos
```

**Por qué los atributos son el motor y no el histórico:** de 45 pares
co-ocurrentes, solo **8** aparecen en más de un ticket. Con 42 tickets, un lift de
14 sobre un soporte de 2 es ruido con decimales. El razonamiento completo, con
números, está en **[`docs/decisiones.md`](docs/decisiones.md)**.

**Sustituto** = misma familia funcional, mejor `uso_recomendado` para el perfil de
la plaza. Si el ancla ya es el adecuado, `sustituto` es `null`.
**Complemento** = misma actividad, rol complementario. Nunca de la misma familia.

---

## El inventario nunca se sobrevende

La garantía vive en el `WHERE`, no en Python:

```sql
UPDATE productos SET stock = stock - ?
 WHERE sku = ? AND activo = 1 AND stock >= ?
```

Si `rowcount != 1` se aborta **el ticket entero**. Alrededor: `BEGIN IMMEDIATE`,
WAL, `busy_timeout`, `CHECK (stock >= 0)` como última defensa, y endpoints con
`def` síncrono (nunca `async def`: `sqlite3` bloquea el event loop y el test de
concurrencia dejaría de significar nada).

Verificado con **50 hilos comprando 1 unidad contra stock 8**: exactamente 8
éxitos, stock final 0.

`POST /api/compras` acepta `Idempotency-Key`: si el vendedor pulsa Cobrar dos
veces, devuelve el ticket original sin volver a descontar.

---

## La capa de IA (opcional)

```bash
python scripts/redactar_justificaciones.py   # requiere GEMINI_API_KEY
```

Gemini reescribe las justificaciones en lenguaje de mostrador. **El LLM no decide
qué se recomienda ni en qué orden: solo redacta.**

> plantilla → `Para soldadura: completa el equipo.`
> LLM → `Llévese el regulador para completar su equipo de soldadura.`

Es **batch, no runtime**: el vendedor tiene un cliente enfrente y no puede esperar
una llamada de red; el evaluador no debería necesitar API key para arrancar; y el
ranking debe ser determinista para poder evaluarse. **Sin clave el script avisa,
no escribe nada y todo el sistema funciona igual** con las plantillas.

**Sobre `GEMINI_MODEL`:** se eligió por **cuota, no por capacidad**. El alias
`gemini-flash-latest` resuelve a 3.7 Flash, que en tier gratuito da 5 peticiones
por minuto y **20 al día**; con 151 relaciones que redactar, el script se pasaba el
rato reintentando `429`. `gemini-3.1-flash-lite` da 15 y **500**: 151/151 en ocho lotes, cero
reintentos. Reescribir una frase de una línea no necesita el modelo más
capaz, necesita poder ejecutarse. El recorrido completo (incluido que
`gemini-2.0-flash` ya devuelve 404) está en `docs/decisiones.md`.

---

## Estructura

```
backend/app/
├── routers/         HTTP → servicios. Nunca abren transacciones
│                    productos · compras · recomendaciones · relaciones
├── services/        Lógica de negocio y LÍMITE TRANSACCIONAL
│                    catalogo · compra · recomendacion · relaciones
├── repositories/    Todo el SQL. Los servicios no conocen SQLite
│                    productos · ventas · relaciones
└── recomendador/
    ├── base.py       Protocol FuenteRecomendacion + Candidato
    ├── historico.py  Co-ocurrencia + Wilson
    ├── perfiles.py   Perfil de plaza × ambiente del producto
    ├── atributos.py  Familias, actividades y roles (dominio declarado)
    └── ranking.py    Mezcla + filtros duros

frontend/
├── app/             layout + 3 vistas (Mostrador, Catálogo, Relaciones)
├── lib/             api.ts (único cliente HTTP), contexto de tienda,
│                    notificaciones, visual
├── hooks/           uno por recurso
└── componentes/     presentación pura, sin fetch
```

**Sin fotos de producto**: cada uno es un icono por categoría + chip de color por
ambiente + SKU en monoespaciada. Una foto genérica que no corresponde al material
contradice la tesis del proyecto.

---

# Arquitectura

Esta sección explica **por qué** el código está escrito así y **qué se descartó**.
El criterio de fondo fue el mismo en todas las decisiones: *esto es una POC de 28
productos que un humano tiene que poder auditar y su autor defender en
entrevista*. Cada capa que no se gane su sitio es ruido.

## 1. Arquitectura de sistema

Dos procesos independientes, un archivo de base de datos.

```
┌────────────────────┐         HTTP/JSON        ┌────────────────────────┐
│  Next.js  :3000    │  ───────────────────▶    │   FastAPI  :8000       │
│  navegador         │  ◀───────────────────    │   (uvicorn, threadpool)│
│                    │      CORS explícito      └───────────┬────────────┘
│  TanStack Query    │                                      │
│  = caché de estado │                          ┌───────────▼────────────┐
│    de servidor     │                          │  SQLite (WAL)          │
└────────────────────┘                          │  ferreteria.db         │
                                                └────────────────────────┘
        scripts fuera del ciclo de petición ─────────────▲
        seed · construir_relaciones · evaluar · redactar_justificaciones
```

**Por qué dos procesos y no uno.** El enunciado fija Python + FastAPI para el
backend. Con eso dado, el frontend es necesariamente otro proceso. La frontera
es HTTP con CORS explícito y un único cliente en `lib/api.ts`.

**Alternativas que se descartaron:**

| Alternativa | Por qué no |
|---|---|
| **Next full-stack** (route handlers + Prisma, sin FastAPI) | El enunciado fija Python + FastAPI. Además perdería el control fino de la transacción SQLite, que es el requisito crítico |
| **Server Components leyendo FastAPI** | Duplica el modelo de datos en TypeScript y en Pydantic, y obliga a decidir en cada vista qué se renderiza en servidor y qué en cliente. El apéndice del enunciado lo prohíbe explícitamente, y con razón |
| **Next como BFF** (proxy `/api/*` → FastAPI) | Añade un salto de red y un segundo sitio donde traducir errores, a cambio de nada: ambos corren en localhost y no hay secretos que ocultar al navegador |
| **Monolito con plantillas Jinja** | Descarta React, que el enunciado pide, y complica el mostrador, que es una pantalla con mucho estado local (ticket en curso) |

**Los scripts están fuera del ciclo de petición a propósito.** `seed`,
`construir_relaciones`, `evaluar` y `redactar_justificaciones` son procesos
batch. Nada de lo que hacen —recalcular reglas, llamar a un LLM, evaluar 89
pliegues— debe ocurrir mientras un vendedor espera con un cliente enfrente.

## 2. Arquitectura de aplicación (backend): capas

```
  routers/          Traduce HTTP ↔ dominio. Sin lógica, sin SQL, sin transacciones
     │              Sabe de: FastAPI, códigos de estado
     ▼
  services/         Reglas de negocio y LÍMITE TRANSACCIONAL (BEGIN/COMMIT)
     │              Sabe de: dominio. NO sabe de FastAPI ni de sqlite3
     ▼
  repositories/     Todo el SQL, en métodos con nombre de negocio
     │              Sabe de: sqlite3 y del esquema
     ▼
  sqlite3
```

La regla que mantiene esto honesto: **un router nunca abre una transacción y un
servicio nunca importa FastAPI**. Por eso los tests de concurrencia pueden llamar
a `compra_service.comprar()` con una conexión propia y 50 hilos sin levantar la
API: se está probando la transacción, que es donde vive la garantía, y no el
threadpool del framework.

Es una regla comprobable, no una intención:

```bash
grep -rn --include="*.py" "BEGIN IMMEDIATE" app/routers/    # 0 resultados
grep -rn "fastapi" app/services/ app/repositories/          # 0 resultados
grep -rn "fetch(" ../frontend/componentes/ ../frontend/app/ # 0 resultados
```

*(Escribir esta sección destapó que `routers/relaciones.py` era la única
excepción: abría la transacción dentro del router. Se extrajo a
`services/relaciones_service.py`. Documentar una arquitectura obliga a
verificarla.)*

**Por qué capas y no arquitectura hexagonal / clean / onion.** Ports & adapters
exige definir una interfaz por cada dependencia externa. Aquí habría una interfaz
`RepositorioProductos` con exactamente una implementación, para siempre. Eso es
ceremonia: añade un archivo y una indirección por cada operación y no compra nada
—ni sustituibilidad real, ni testabilidad que no tengamos ya (los tests usan una
base temporal real, que además prueba el SQL de verdad).

**Dónde SÍ se invierte la dependencia, y por qué ahí.** En un único punto:
`recomendador/base.py` define el `Protocol FuenteRecomendacion`. Ahí sí hay
múltiples implementaciones hoy (`HistoricoStrategy`, `AtributosStrategy`) y se
esperan más mañana. La inversión se paga sola; en el resto del sistema no.

**Lo que tampoco se usó, y por qué:**

- **CQRS** — no hay asimetría lectura/escritura que lo justifique. Las mismas
  filas se leen y se escriben, y el volumen es de 28 productos.
- **Event sourcing** — `movimientos_inventario` ya es un libro append-only que
  permite reconstruir el stock sumando deltas. Eso da la trazabilidad sin
  reescribir todo el modelo como eventos.
- **Unit of Work abstracto** — la conexión de sqlite3 ya *es* la unidad de
  trabajo, con `BEGIN IMMEDIATE` / `commit` / `rollback`. Envolverla en una clase
  propia sería renombrarla.
- **Capa de mappers / DTOs aparte** — los esquemas Pydantic ya son el contrato
  de entrada y salida. Una capa extra de conversión entre `Row` y modelo de
  dominio y modelo de respuesta, con 9 campos, es trabajo por triplicado.

## 3. Patrones de diseño, y dónde exactamente

### 3.1 Repository — `repositories/*.py`

Todo el SQL vive aquí. **No es un repositorio genérico**: no hay
`Repository<T>.update()`. Los métodos se llaman como la operación de negocio que
representan.

```python
def descontar_stock(bd, sku: str, cantidad: int) -> int:
    cur = bd.execute(
        """UPDATE productos SET stock = stock - ?, actualizado_en = datetime('now')
            WHERE sku = ? AND activo = 1 AND stock >= ?""",
        (cantidad, sku, cantidad),
    )
    return cur.rowcount
```

Un `update(sku, {"stock": n})` genérico habría hecho imposible expresar la
condición `stock >= ?`, que es precisamente la garantía del sistema. El patrón
existe para esconder SQL, no para esconder intención.

### 3.2 Service Layer — `services/*.py`

Aquí vive la lógica de negocio **y el límite transaccional**. La razón de que la
transacción esté aquí y no en el repositorio: un ticket toca varias filas de
varias tablas (`productos`, `ventas`, `movimientos_inventario`, `operaciones`) y
o entra todo o no entra nada. Solo la capa que conoce la operación completa puede
decidir dónde empieza y acaba.

Y no está en el router porque entonces el límite dependería del transporte: la
misma compra llamada desde un test o desde un script no tendría transacción.

### 3.3 Strategy — `recomendador/`

```python
class FuenteRecomendacion(Protocol):
    nombre: str
    def generar(self, sku: str, tienda: str) -> list[Candidato]: ...
```

Se usa `Protocol` (tipado estructural) y no una clase base abstracta. La
diferencia importa y **se cobra en `scripts/evaluar.py`**: la evaluación necesita
reglas construidas *sin* el ticket que está midiendo, así que define su propia
`HistoricoEnMemoria` que cumple el Protocol **sin heredar de nada ni importar el
módulo original**. Con una ABC habría que heredar y arrastrar el constructor que
recibe una conexión.

Añadir una fuente (un modelo, una API externa, reglas de temporada) es añadir una
clase. Ni `ranking.py` ni el servicio ni la API se tocan.

### 3.4 Inyección de dependencias — `Depends` de FastAPI

```python
def obtener_bd() -> Iterator[sqlite3.Connection]:
    conexion = conectar()
    try:
        yield conexion
    finally:
        conexion.close()          # se ejecuta DESPUÉS de enviar la respuesta

@router.get("/{sku}", response_model=Producto)
def obtener(sku: str, bd: sqlite3.Connection = Depends(obtener_bd)) -> dict:
    return catalogo_service.obtener(bd, sku)
```

FastAPI resuelve la dependencia por petición: ejecuta el generador hasta el
`yield`, inyecta la conexión, y al terminar la respuesta corre el `finally`.

**Por qué una conexión por petición y no una global:** `sqlite3` asocia la
conexión al hilo que la creó. FastAPI atiende los endpoints `def` en un
threadpool, así que una conexión global se usaría desde hilos distintos. Se abre
con `check_same_thread=False` porque la conexión se crea y se usa dentro del mismo
hilo de trabajo, pero sqlite3 no puede comprobarlo solo.

**Por qué no un pool de conexiones:** SQLite es un archivo, no un servidor. Con
WAL hay un escritor y muchos lectores concurrentes; el "pool" es el sistema
operativo. Un pool en Python añadiría estado compartido entre hilos —justo lo que
se quiere evitar.

**Lo que la DI compra en los tests:** `conftest.py` hace
`monkeypatch.setattr(modulo_db, "RUTA_BD", ruta_temporal)`. Como todo pasa por
`conectar()`, tanto la dependencia de FastAPI como los 50 hilos del test de
concurrencia apuntan a la misma base temporal, sin tocar una línea de producción.

**Por qué los endpoints son `def` y no `async def`:** `sqlite3` es bloqueante. Con
`async def` bloquearían el event loop y las peticiones se serializarían de facto;
el test de concurrencia dejaría de medir lo que dice medir. Con `def`, FastAPI los
ejecuta en su threadpool y la concurrencia es real.

### 3.5 Clave de idempotencia — `POST /api/compras`

No es un patrón GoF sino de integración, y es el que evita el cobro doble:

```python
if clave and not ventas_repo.reservar_clave(bd, clave):   # INSERT contra la PK
    bd.rollback()
    return {**json.loads(ventas_repo.leer_respuesta(bd, clave)), "repetida": True}
```

La reserva es el propio `INSERT` contra la clave primaria de `operaciones`, así
que **no hay ventana entre comprobar y reservar**. Si dos peticiones idénticas
llegan a la vez, la segunda queda bloqueada por `BEGIN IMMEDIATE` hasta que la
primera confirme, y entonces su `INSERT` falla y devuelve la respuesta guardada.

## 4. Por qué el recomendador está construido así

El enunciado deja libre el cómo, y esa decisión es parte central de lo que se
evalúa. Se consideraron cuatro caminos:

| Enfoque | Por qué se descartó (o se usó) |
|---|---|
| **Filtrado colaborativo item-item** | Necesita señal de co-ocurrencia densa. Aquí hay 42 tickets y solo 8 pares repetidos: la matriz es casi toda ceros |
| **Factorización de matrices / ALS** | Necesita identificador de cliente para construir la matriz usuario × ítem. **`sales.csv` no tiene ninguno** |
| **Embeddings del catálogo con un LLM** | Tentador con 28 descripciones, pero no es determinista, no se puede evaluar offline de forma reproducible, y convierte cada recomendación en una llamada de red en la pantalla del vendedor |
| **Reglas de asociación solas** | Es lo que los datos sugieren a primera vista, y está **medido que no basta**: sobre 7 pares de dominio que nunca co-ocurren recupera 0/7 |
| **Híbrido: atributos como motor + reglas como evidencia** | ✅ El elegido. Cubre el catálogo completo sin necesitar ventas previas, y cuando hay evidencia real la cita, que es lo que convence a un cliente |

**Tres decisiones de diseño dentro del recomendador:**

**a) Asimetría deliberada entre las dos fuentes.** El histórico se *materializa*
en la tabla `relaciones` (solo cambia cuando cambian las ventas; recalcularlo por
petición sería trabajo tirado). Los atributos se *calculan al servir*, porque el
sustituto correcto depende del perfil de la sucursal y materializarlo exigiría una
fila por (origen, destino, plaza). El efecto secundario bueno: **un producto dado
de alta hoy recibe sugerencias sin reconstruir nada** — hay un test que lo prueba.

**b) Los filtros duros viven en un solo punto**, `ranking.mezclar`. No están
repartidos por las estrategias porque el requisito «nunca recomendar algo agotado»
se cumple o se rompe en un sitio, y así hay un único lugar que auditar y que
testear. De hecho un bug real lo confirmó: la exclusión de misma familia estaba
dentro de `AtributosStrategy`, y el histórico la reintroducía por detrás.

**c) Normalización por fuente y no global.** Cada fuente entrega scores en 0..1
*dentro de su escala*; la comparación entre fuentes la hace el ranking
multiplicando por el peso configurable. Así se puede subir o bajar una fuente
entera desde el panel sin recalcular nada.

## 5. Arquitectura del frontend

La distinción que ordena todo el frontend es **estado de servidor vs estado de
cliente**:

| Tipo de estado | Quién lo gestiona | Ejemplos |
|---|---|---|
| De servidor (vive en la BD, puede quedar obsoleto) | **TanStack Query** | productos, recomendaciones, relaciones, pesos |
| Global de cliente (solo existe en el navegador) | **Context**, uno solo | sucursal seleccionada |
| Local de una vista | `useState` en la página | ticket en curso, texto del buscador, fila en edición |
| Efímero de UI | `useState` en el componente | acordeón abierto, índice resaltado |

**Por qué no Redux ni Zustand.** Un store global existe para compartir estado
entre partes lejanas del árbol. Aquí lo único verdaderamente global es la
sucursal —un string— y lo demás o es de servidor (y entonces el problema real no
es guardarlo sino *invalidarlo*, que es justo lo que TanStack Query resuelve) o
es local a una vista. Un store añadiría una segunda copia de los datos que ya
están en la caché de Query, con el riesgo clásico de que las dos discrepen.

**La invalidación es funcional, no cosmética.** Tras cobrar:

```ts
cliente.invalidateQueries({ queryKey: ["productos"] });
cliente.invalidateQueries({ queryKey: ["recomendaciones"] });
```

Sin esto la interfaz seguiría mostrando el stock anterior y **podría ofrecer un
producto recién agotado**, rompiendo un requisito bloqueante desde el frontend.

**Capas de componentes:**

```
app/*/page.tsx      Orquestación: estado de la vista y composición
      │             Es el único que conoce hooks de datos
      ▼
hooks/use*.ts       Acceso a datos y invalidación. Uno por recurso
      │
      ▼
lib/api.ts          Único cliente HTTP. Ningún componente hace fetch
      │
componentes/*.tsx   Presentación pura: reciben props, no piden datos
```

Que los componentes sean puros no es dogma: es lo que permite que
`ProductoTile` se use igual en el buscador, en las tarjetas de recomendación, en
el catálogo y en el ticket sin que cada uso dispare su propia petición.

**Por qué un único cliente HTTP.** Si el manejo de errores viviera repartido en
cada componente, el mensaje «No hay suficiente inventario de SKU007. Quedan 3»
dependería de quién escribió cada llamada. `lib/api.ts` normaliza la respuesta de
error de FastAPI —incluida la lista de errores de validación de Pydantic, que
tiene otra forma— en una única clase `ErrorApi` que lleva `sku` y `disponible`.

## 6. Diseño de la API

Orientada a recursos, sin ceremonia REST que no aporte:

| Decisión | Por qué |
|---|---|
| `PATCH` y no `PUT` para productos | La edición del catálogo es parcial (precio y existencia). Un `PUT` obligaría a enviar el recurso completo y a arriesgar pisar campos con defaults |
| `DELETE` → `204` y borrado **lógico** | `ventas` y `movimientos_inventario` referencian el SKU; un borrado real rompería la trazabilidad. Se devuelve 204 porque no hay cuerpo que devolver |
| `Idempotency-Key` como **cabecera** | Es metadato de transporte, no parte del ticket. Va donde va en cualquier pasarela de pago |
| `excluir=SKU,SKU` como query param | La recomendación es una lectura: tiene que ser `GET`, cacheable e idempotente. Meter el ticket en un cuerpo obligaría a `POST` y mentiría sobre la semántica |
| El error lleva `sku` y `disponible` | El mostrador necesita el número para decir «Quedan 3», no solo un texto que tendría que parsear |
| Un `exception_handler` central | Traduce excepciones de dominio a códigos de estado en un solo sitio. Es lo que permite que los servicios no importen FastAPI |

## 7. Modelo de datos

| Decisión | Por qué |
|---|---|
| `CHECK (stock >= 0)` | Última defensa. La primera es el `WHERE` del `UPDATE`; esto protege de un `UPDATE` mal escrito en el futuro |
| `movimientos_inventario` append-only | Auditoría de por qué el stock vale lo que vale. Un test comprueba que la suma de deltas cuadra con el stock final |
| `UNIQUE(sku_origen, sku_destino, tipo)` | Una fila por par. Consecuencia: si ambas fuentes proponen el mismo par, gana el histórico porque lleva soporte, confianza y lift. La regla por atributos sigue actuando al servir |
| `estado` y `peso_manual` separados del `score` | El score lo calcula la máquina y se recalcula; el ajuste lo pone una persona y **sobrevive a reconstruir las reglas**. Si no, el panel sería papel mojado |
| `justificacion_ia` en columna aparte | Permite revertir al texto de plantilla, auditar qué escribió la máquina, y limpiarla sola cuando cambia la plantilla (señal de que los números que redactó ya no son ciertos) |
| `tiendas.id` slug ASCII, `nombre` con acento | `sales.csv` trae `Cancún`; arrastrar acentos a ids, URLs y joins es una fuente segura de bugs de encoding |

---

## API

```
GET    /api/tiendas
GET    /api/productos?q=&tienda=&incluir_inactivos=
GET    /api/productos/{sku}
POST   /api/productos
PATCH  /api/productos/{sku}
DELETE /api/productos/{sku}                 borrado lógico
POST   /api/compras                         header: Idempotency-Key
GET    /api/recomendaciones?sku=&tienda=&excluir=SKU,SKU
GET    /api/relaciones?tipo=&fuente=
PATCH  /api/relaciones/{id}                 { estado, peso_manual }
GET    /api/config/pesos
PUT    /api/config/pesos
```

Documentación interactiva en `http://localhost:8000/docs`.

---

# Alternativas consideradas y siguientes pasos

## 1. Vite en vez de Next: el razonamiento honesto

**Se entregó con Next porque es lo que se pidió.** Pero conviene dejar por
escrito que, mirando solo lo técnico, **Vite habría sido la elección natural para
esta aplicación concreta**, y por qué.

Next aporta valor cuando hay: SEO, contenido público indexable, renderizado en
servidor, streaming, generación estática, optimización de imágenes o rutas de API
en el mismo proceso.

Este sistema **no tiene ninguna de esas necesidades**:

- Es una **herramienta interna de mostrador**. Nadie la busca en Google; en
  producción iría detrás de un login.
- **No hay contenido público** ni URLs que compartir.
- **No hay imágenes** — la tesis del proyecto es justamente que un icono
  determinista comunica el material mejor que una foto genérica.
- **El backend ya existe** y es FastAPI, así que las route handlers de Next
  sobran.
- Todo el estado que importa es **estado de servidor cacheado en el cliente**
  (TanStack Query) más un ticket en curso que vive en memoria. Nada de eso se
  beneficia de SSR.

Y de hecho, **las restricciones del propio apéndice del enunciado dejan Next
funcionando casi exactamente como Vite**: todas las vistas son `"use client"`,
sin Server Components consumiendo la API, sin Server Actions, sin middleware, sin
`next/image`. De Next se usan en la práctica dos cosas: **enrutado por ficheros**
y **`next/font/google`** (que autohospeda las fuentes y evita el parpadeo).

**Lo que cuesta la decisión:** en producción, Next exige un proceso Node
corriendo. Vite habría compilado a estáticos que sirve cualquier CDN —o el propio
FastAPI— y la operación tendría **un proceso menos que vigilar**. Para una
ferretería con cinco tiendas, eso no es trivial.

**Por qué se entregó igualmente con Next:** el enunciado lo lista como stack
válido y su apéndice describe la variante con detalle. Cuando el cliente fija una
tecnología, la discusión razonable es documentar el criterio, no ignorarlo. Si
esto pasara a producción, esta sección sería la conversación a tener.

## 2. Los datos de Mérida: qué haría y por qué NO lo hice aquí

Mérida no aparece en `sales.csv`. Es un arranque en frío completo y **deliberado**
en los datos del enunciado.

**Lo que NO se hizo, a propósito: inventar ventas para Mérida.** Habría sido
fácil generar tickets sintéticos copiando el patrón de Cancún —misma costa, mismo
perfil salino— y todas las métricas habrían mejorado. Sería un error grave por
dos razones: contamina la evaluación con datos que nadie observó, y **esconde
justo el problema interesante**, que es demostrar que el sistema responde bien sin
historial. El 0/7 del histórico frente al 6/7 de los atributos deja de significar
nada si se rellena el hueco a mano.

**Cómo lo resolvería en producción, en orden de preferencia:**

1. **Onboarding de sucursal (lo que realmente haría).** Al dar de alta una tienda,
   el sistema pregunta tres cosas al encargado: ¿ambiente costero, sol directo,
   interior o taller?, ¿clientes de obra o de mantenimiento?, ¿qué tres categorías
   se mueven más? Con eso queda un perfil declarado por quien conoce la plaza, y
   no adivinado. Es exactamente lo que hoy está cableado en `TIENDAS` de
   `seed.py`, pero puesto donde debe estar: en manos del negocio.
2. **Préstamo de vecino por perfil.** Mientras Mérida no tenga ventas propias,
   heredar las reglas históricas de Cancún con un peso reducido (p. ej. 0.5) y
   marcarlas visiblemente como *«prestado de Cancún»* en el panel de Relaciones.
   El negocio ve de dónde sale y puede rechazarlo.
3. **Decaimiento automático.** Conforme Mérida acumula tickets propios, el peso
   de lo prestado baja hasta desaparecer. Sin intervención manual y sin un salto
   brusco el día que cruce un umbral.

Requiere una columna de origen en `relaciones` (`prestado_de`) y una dimensión de
tienda en las reglas históricas — hoy no la tienen porque no hacía falta.

## 3. Módulo de tickets: lo que falta para ser un punto de venta

Hoy se cobra y el inventario baja, pero **el ticket se pierde en cuanto se cierra
la pantalla**. Es la carencia más visible para alguien que pruebe el sistema. Lo
bueno es que la base ya está preparada:

- **Historial de tickets** (`GET /api/compras`, `GET /api/compras/{id}`). Los
  datos ya se guardan en `ventas` agrupados por `ticket_id`; falta exponerlos y
  una vista con filtro por fecha y sucursal.
- **Devoluciones y cancelaciones.** Aquí el diseño ya paga: `movimientos_inventario`
  es append-only, así que una devolución **no borra nada** — inserta un movimiento
  con `delta` positivo y `motivo = 'devolucion'`. El stock se reconstruye sumando
  y la auditoría queda intacta.
- **Corte de caja.** Total por sucursal y día, con desglose por método de pago
  (que hoy no existe: habría que añadirlo a `ventas`).
- **Reimpresión.** Un ticket recuperable por `ticket_id`.
- **Tasa de aceptación de sugerencias.** La métrica que de verdad importa, y hoy
  no se registra: hay que guardar si una línea entró al ticket *desde una
  sugerencia* y de qué fuente. Sin eso no se puede responder «¿está subiendo las
  ventas?», que es la pregunta del cliente. **Sería lo primero que añadiría.**

## 4. Otras funcionalidades que valdría la pena

| Idea | Por qué importa | Qué costaría |
|---|---|---|
| **Lector de código de barras** | En un mostrador real nadie teclea el nombre. El buscador ya acepta SKU: un lector es un teclado que escribe y pulsa Enter | Casi nada; sobre todo decidir el formato de código |
| **`familia` como columna del maestro** | Hoy es una constante en `atributos.py` y un alta nueva no entra en ninguna familia hasta tocar código | Columna + selector en el catálogo |
| **Reconstrucción automática de relaciones** | Tras un alta, el producto recibe complementos al vuelo pero no aparece en el panel hasta reconstruir | Disparador tras el alta o tarea nocturna |
| **Autenticación y roles** | El panel de Relaciones y el CRUD no pueden estar abiertos. La sucursal debería venir del usuario, no elegirse a mano | OAuth2 con scopes `vendedor` / `encargado` |
| **Alertas de reabastecimiento** | El sistema ya sabe qué está por agotarse y qué se vende junto; podría avisar antes de la rotura de stock | Consulta sobre `movimientos_inventario` |
| **A/B en mostrador** | Es la única forma de demostrar que las recomendaciones suben ventas. Lo offline sirve para no salir a ciegas, no para declarar victoria | Requiere primero la tasa de aceptación |
| **Sugerencias por temporada** | Época de lluvias e impermeabilizantes, por ejemplo. Encaja como **una clase nueva** que cumpla `FuenteRecomendacion` | Es justo el caso para el que se eligió Strategy |

## 5. Fuera de alcance en esta POC

Autenticación y roles · `familia` como columna del maestro · reconstrucción
automática de relaciones tras un alta · historial y devoluciones de tickets ·
personalización por cliente (no hay identificador de cliente en los datos) · A/B
en mostrador.

Cada uno, con cómo lo resolvería, en **[`docs/decisiones.md`](docs/decisiones.md)**.
