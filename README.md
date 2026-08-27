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
| Cambia la tienda a **Mérida** | Busca `tornillo` → propone **inoxidable 316**, con **cero historial** en esa plaza. El acento de toda la UI cambia con la plaza |
| **Relaciones** (`/relaciones`) | Bloquea `SKU001 → SKU004`. Vuelve al mostrador: **desapareció, sin reiniciar nada** |
| **Catálogo** (`/catalogo`) | Pon el stock de un producto en 0 → sale del mostrador y de las recomendaciones |

Atajo: `/` enfoca el buscador desde cualquier parte; flechas recorren y Enter
selecciona.

---

## Comprobar que funciona

```bash
cd backend
pytest -v                    # 35 tests, incluye 50 hilos contra stock 8
python scripts/evaluar.py    # tabla real contra 4 baselines
```

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
├── services/        Lógica de negocio y LÍMITE TRANSACCIONAL
├── repositories/    Todo el SQL. Los servicios no conocen SQLite
└── recomendador/
    ├── base.py       Protocol FuenteRecomendacion + Candidato
    ├── historico.py  Co-ocurrencia + Wilson
    ├── perfiles.py   Perfil de plaza × ambiente del producto
    ├── atributos.py  Familias, actividades y roles (dominio declarado)
    └── ranking.py    Mezcla + filtros duros

frontend/
├── app/             layout + 3 vistas (Mostrador, Catálogo, Relaciones)
├── lib/             api.ts (único cliente HTTP), contexto de tienda, visual
├── hooks/           uno por recurso
└── componentes/     presentación pura, sin fetch
```

**Sin fotos de producto**: cada uno es un icono por categoría + chip de color por
ambiente + SKU en monoespaciada. Una foto genérica que no corresponde al material
contradice la tesis del proyecto.

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

## Fuera de alcance

Autenticación y roles · `familia` como columna del maestro en vez de constante ·
reconstrucción automática de relaciones tras un alta · A/B en mostrador para medir
lo único que de verdad importa (tasa de aceptación y ticket promedio) ·
personalización por cliente (no hay identificador de cliente en los datos).

Cada uno, con cómo lo resolvería, en **[`docs/decisiones.md`](docs/decisiones.md)**.
