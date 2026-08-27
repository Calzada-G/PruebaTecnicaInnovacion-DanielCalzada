# La API, ruta por ruta

Documentación de referencia de la API REST. Explica **qué hace cada ruta, por
qué existe, quién la consume y qué devuelve exactamente**.

La documentación interactiva vive en **http://localhost:8000/docs** (Swagger UI)
y se genera sola desde el código: si un día no coinciden, manda `/docs`, porque
sale del mismo sitio del que sale la respuesta. Este archivo existe para lo que
Swagger no puede contar: el porqué.

---

## Índice

1. [Convenciones](#1-convenciones)
2. [Por qué son quince operaciones y no más](#2-por-qué-son-quince-operaciones-y-no-más)
3. [Catálogo — `/api/productos`](#3-catálogo--apiproductos)
4. [Cobro — `/api/compras`](#4-cobro--apicompras)
5. [Recomendaciones — `/api/recomendaciones`](#5-recomendaciones--apirecomendaciones)
6. [Relaciones y pesos — `/api/relaciones`, `/api/config/pesos`](#6-relaciones-y-pesos)
7. [Diagnóstico — `/api/diagnostico`](#7-diagnóstico--apidiagnostico)
8. [Sucursales — `/api/tiendas`](#8-sucursales--apitiendas)
9. [Estado — `/` y `/api/salud`](#9-estado--y-apisalud)
10. [Qué es `additionalProp1`](#10-qué-es-additionalprop1)
11. [Decisiones REST y por qué](#11-decisiones-rest-y-por-qué)
12. [Cómo probar todo esto](#12-cómo-probar-todo-esto)

---

## 1. Convenciones

| | |
|---|---|
| **Base** | `http://localhost:8000` |
| **Formato** | JSON en peticiones y respuestas. Sin envoltorio: una lista devuelve una lista, no `{"data": [...]}` |
| **Idioma** | Rutas, campos y parámetros en español, como el resto del código. `sku`, `stock` y `lift` se quedan en inglés porque así se llaman en la ferretería y en la literatura de reglas de asociación |
| **Autenticación** | No hay. Está declarado como fuera de alcance: en producción sería OAuth2 con perfiles `vendedor` y `encargado` |
| **Fechas** | `YYYY-MM-DD`, texto plano |

### `tienda` no filtra el inventario

Aparece en casi todas las rutas y **es el parámetro que más se malinterpreta**.
El inventario es **uno solo, compartido por las cinco sucursales**: el stock de
`SKU001` es el mismo en Cancún y en CDMX. Lo que cambia según la plaza es:

| Ruta | Qué hace `tienda` |
|---|---|
| `GET /api/productos` | **Ordena**. Pone delante lo que más se mueve en esa plaza |
| `GET /api/recomendaciones` | **Cambia el resultado**. El sustituto depende del clima de la zona |
| `POST /api/compras` | **Registra** dónde se cobró. El descuento es del inventario común |
| `GET /api/diagnostico` | **Cambia el resultado**. Cada plaza tiene otras carencias |

Un slug inexistente da **404 en las cuatro**. Antes `GET /api/productos` era la
excepción: respondía `200` con el orden alfabético, así que un `tienda=cdxm` mal
escrito devolvía un catálogo que parecía correcto. Es el tipo de error que no se
descubre hasta producción.

### Códigos de estado

| Código | Cuándo |
|---|---|
| `200` | Lectura correcta, o escritura que devuelve el recurso |
| `201` | Alta de producto, cobro de ticket |
| `204` | Baja lógica. Sin cuerpo: no hay nada que devolver |
| `400` | Producto dado de baja que se intenta vender |
| `404` | SKU, sucursal o relación inexistente |
| `409` | SKU duplicado, o inventario insuficiente |
| `422` | El cuerpo o los parámetros no cumplen el contrato |

**Todo error trae `detail` con un texto legible.** El `409` de compra trae además
`sku` y `disponible`, porque el mostrador necesita el número para escribir
«Quedan 3» y no debería sacarlo del texto con una expresión regular:

```json
{ "detail": "No hay suficiente inventario de SKU007. Quedan 3.",
  "sku": "SKU007", "disponible": 3 }
```

El `422` lo genera Pydantic y trae una **lista** con la ruta del campo que falló:

```json
{ "detail": [ { "type": "string_pattern_mismatch",
                "loc": ["body", "sku"],
                "msg": "String should match pattern '^[A-Za-z0-9][A-Za-z0-9_-]{1,23}$'" } ] }
```

Que sea lista y no texto es deliberado: un formulario con ocho campos necesita
saber **cuál** falló para marcarlo. El cliente HTTP del frontend une los `msg`
en una frase cuando solo hay que enseñar un aviso.

---

## 2. Por qué son quince operaciones y no más

Cada una existe porque algo concreto la llama. Trece las consume la interfaz;
dos son para el operador.

| # | Operación | Quién la usa | Qué se rompe sin ella |
|---|---|---|---|
| 1 | `GET /api/productos` | Buscador del mostrador y tabla de catálogo | No hay qué vender ni qué buscar |
| 2 | `GET /api/productos/{sku}` | Ficha al elegir en el mostrador | La ficha mostraría datos viejos de la lista |
| 3 | `POST /api/productos` | Alta en Catálogo | El catálogo sería de solo lectura (el PDF pide CRUD) |
| 4 | `PATCH /api/productos/{sku}` | Edición en línea de precio y existencia | No se corrige un precio sin tocar la base a mano |
| 5 | `DELETE /api/productos/{sku}` | Botón de baja | Un producto descontinuado se seguiría ofreciendo |
| 6 | `POST /api/compras` | Botón Cobrar | **Es el requisito bloqueante**: descontar sin sobrevender |
| 7 | `GET /api/recomendaciones` | Los dos bloques del mostrador | Es el objeto del encargo |
| 8 | `GET /api/relaciones` | Pantalla de Relaciones | El sistema sería una caja negra: nadie ve por qué sugiere lo que sugiere |
| 9 | `PATCH /api/relaciones/{id}` | Bloquear / fijar / ajustar | El negocio no podría corregir una sugerencia mala |
| 10 | `GET /api/config/pesos` | Modo activo en Relaciones | El panel no sabría qué preajuste está puesto |
| 11 | `PUT /api/config/pesos` | Los tres preajustes | No se podría decidir cuánto pesa la evidencia frente al criterio |
| 12 | `GET /api/diagnostico` | Banda de mejoras del Catálogo | Nadie sabría que Mérida no tiene ventas ni qué falta por dar de alta |
| 13 | `GET /api/tiendas` | Selector de sucursal | Es la **primera** llamada: sin ella no hay `tienda` que mandar |
| 14 | `GET /api/salud` | **Nadie desde la interfaz.** El operador | Nada, funcionalmente. Es lo que responde «¿está viva y sembrada?» sin abrir la UI, y lo que consultaría un monitor o el *healthcheck* de un contenedor |
| 15 | `GET /` | Una persona con un navegador | Nada. Antes devolvía `{"detail":"Not Found"}`, que no dice si la API arrancó bien |

**Las 14 y 15 son las únicas que no consume el frontend, y es a propósito.** Un
servicio que no sabe decir en qué estado está solo se diagnostica leyendo logs.

**Lo que deliberadamente NO existe**, aunque cabría esperarlo:

- `GET /api/compras` (historial de tickets) — los datos ya están en `ventas`,
  pero nada los pide todavía. Está en el README como lo primero que se añadiría.
- `PUT /api/productos/{sku}` — sobra teniendo `PATCH`. Ver §11.
- `DELETE /api/relaciones/{id}` — una relación no se borra, se **bloquea**: si
  se borrara, la siguiente reconstrucción la traería de vuelta como si nadie la
  hubiera rechazado nunca.
- Rutas de sesión o usuarios — no hay autenticación en esta POC.

---

## 3. Catálogo — `/api/productos`

### `GET /api/productos`

Catálogo vendible, ordenado según la plaza que pregunta.

| Parámetro | Tipo | Por defecto | Qué hace |
|---|---|---|---|
| `buscar` | texto | — | Texto libre. Busca **a la vez** en nombre, SKU, categoría, material y uso recomendado |
| `tienda` | slug | — | Ordena por lo que más se mueve ahí. `404` si no existe |
| `incluir_inactivos` | bool | `false` | Incluye los dados de baja |

> **Por qué `buscar` y no `q`.** `q` es una convención heredada de los buscadores
> web, pero en esta API todos los demás parámetros están en español y dicen lo
> que hacen (`tienda`, `excluir`, `incluir_inactivos`). Una sola letra obligaba a
> abrir el código para saber si buscaba por nombre o por SKU. Busca por los dos,
> y por tres campos más: por eso encuentra por «salino» o por «interior», que es
> justo lo que un vendedor pregunta cuando no recuerda el nombre comercial.

`incluir_inactivos` solo lo manda la vista de Catálogo, donde la baja tiene que
poder revertirse. **El mostrador nunca lo manda**: un producto de baja no se
vende, y ofrecer un producto que no se puede cobrar es peor que no ofrecer nada.

```bash
curl "http://localhost:8000/api/productos?buscar=salino&tienda=cancun"
```

```json
[ { "sku": "SKU007",
    "nombre": "Tornillo acero inoxidable 316 1/4 (caja 100)",
    "descripcion": "Tornillería de máxima resistencia a la corrosión salina",
    "categoria": "fijación",
    "material": "acero inoxidable 316",
    "uso_recomendado": "exterior costero y ambientes salinos",
    "precio": 180.0,
    "stock": 80,
    "activo": true } ]
```

Ninguno de los dos resultados de esa búsqueda —`SKU007` y `SKU025`— lleva
«salino» en el nombre: la palabra está en `material` y en `uso_recomendado`. Ese
es justo el caso de uso.

`activo` es **booleano**, no `0`/`1`. SQLite guarda enteros; el modelo de salida
lo convierte. Un test comprueba que el mismo concepto no viaje como booleano en
una ruta y como entero en otra.

### `GET /api/productos/{sku}`

Ficha de un producto. Devuelve también los dados de baja: la ficha existe aunque
el producto ya no se venda. → `404` si el SKU no existe.

### `POST /api/productos` → `201`

Alta. La existencia inicial queda como **primer movimiento del libro de
inventario**: sin ella, el stock inicial no tendría de dónde salir en una
auditoría.

```json
{ "sku": "SKU029", "nombre": "Disco de corte para metal 7\"",
  "categoria": "consumible", "precio": 75.0, "stock": 20,
  "material": "óxido de aluminio", "uso_recomendado": "corte de metal en taller",
  "descripcion": "Disco abrasivo reforzado para esmeriladora angular" }
```

Obligatorios: `sku`, `nombre`, `categoria`, `precio`, `stock`. Los otros tres
son `""` por defecto — pero `uso_recomendado` **vacío deja al producto sin
sugerencias**, porque de ese campo salen. El diagnóstico lo detecta y lo avisa.

| Regla | Motivo |
|---|---|
| `sku`: `^[A-Za-z0-9][A-Za-z0-9_-]{1,23}$`, a mayúsculas | Viaja en la URL: sin espacios, acentos ni barras. `sku001` y `SKU001` no pueden ser dos productos |
| `nombre`: 2–120 · `categoria`: 2–40 · `material`: ≤60 · `uso_recomendado`: ≤80 · `descripcion`: ≤300 | Los del CSV llegan a 44 caracteres; el tope deja margen sin permitir pegar un PDF entero |
| `precio`: 0 … 9 999 999 · `stock`: 0 … 1 000 000 | Sin tope cabe `1e308`, que rompe cualquier suma posterior |
| Sin caracteres de control en ningún texto | Llegan al pegar desde Excel. No rompen la base (las consultas son parametrizadas) pero descuadran tablas y hacen que dos productos idénticos parezcan distintos |

→ `409` si el SKU ya existe. → `422` si algo incumple la tabla de arriba.

### `PATCH /api/productos/{sku}` → `200`

Edición **parcial**: solo se tocan los campos presentes en el cuerpo, así que dos
personas corrigiendo cosas distintas del mismo producto no se pisan. `sku` no se
puede cambiar: es la clave.

```bash
curl -X PATCH http://localhost:8000/api/productos/SKU001 \
     -H "Content-Type: application/json" -d '{"precio": 470, "stock": 12}'
```

Un cambio de `stock` desde aquí queda registrado como **ajuste de almacén** en
el mismo libro que las ventas, con su propio motivo. Es lo que permite explicar
después por qué el inventario vale lo que vale.

`{"activo": true}` **reactiva** un producto dado de baja.

### `DELETE /api/productos/{sku}` → `204`

Baja **lógica**. El SKU sigue existiendo y desaparece del mostrador y de las
recomendaciones. Nunca se borra la fila porque `ventas` y
`movimientos_inventario` la referencian: borrarla rompería el historial.

**Es idempotente**: repetirlo sobre un producto ya dado de baja vuelve a
responder `204`, no un error. Con dos pestañas abiertas, la segunda no debería
ver un fallo por llegar tarde a algo que ya se cumplió. → `404` solo si el SKU
nunca existió.

---

## 4. Cobro — `/api/compras`

### `POST /api/compras` → `201`

**La ruta crítica del proyecto.**

```bash
curl -X POST http://localhost:8000/api/compras \
     -H "Content-Type: application/json" \
     -H "Idempotency-Key: 8f14e45f-ea0d-4b1c-9a6e-2c1d3b4a5e6f" \
     -d '{"tienda":"cancun","items":[{"sku":"SKU001","cantidad":1},
                                     {"sku":"SKU004","cantidad":2}]}'
```

```json
{ "ticket_id": "T043", "tienda": "cancun", "fecha": "2026-08-27",
  "lineas": [ { "sku": "SKU001", "nombre": "Soplete de gas MAPP",
                "cantidad": 1, "precio_unitario": 450.0,
                "subtotal": 450.0, "stock_restante": 14 } ],
  "total": 690.0, "repetida": false }
```

`stock_restante` viene en cada línea para que la interfaz no tenga que volver a
pedir el catálogo solo para saber cómo quedó el inventario.

**Tres garantías:**

1. **El ticket es atómico.** Si una línea no alcanza, no se descuenta ninguna.
2. **No hay sobreventa.** La comprobación vive dentro del
   `UPDATE ... WHERE stock >= ?`, no en un `SELECT` previo: entre leer y
   escribir cabe otra venta. Un test lanza 50 hilos contra 8 piezas: pasan
   exactamente 8 y el stock final es 0.
3. **Las líneas repetidas del mismo SKU se suman** antes de descontar. Dos de 5
   contra 8 piezas fallan como una de 10; no cuelan 5 y luego otras 5.

**`Idempotency-Key`** (cabecera, opcional pero recomendada): identifica el
**intento** de cobro, no el ticket. Si llegan dos peticiones con la misma clave
—doble clic, reintento de red—, la segunda devuelve **el ticket original** con
`repetida: true` y **no descuenta nada**. Va en cabecera porque es metadato de
transporte, igual que en cualquier pasarela de pago. La clave se reserva con un
`INSERT` contra una PRIMARY KEY dentro de la misma transacción: no hay ventana
entre comprobar y reservar porque son la misma operación.

| Error | Código |
|---|---|
| `tienda` inexistente | `404` |
| Algún SKU inexistente | `404` |
| Sin inventario suficiente | `409` + `sku` + `disponible` |
| Producto dado de baja | `400` |
| `items` vacío, o `cantidad` ≤ 0 | `422` |

---

## 5. Recomendaciones — `/api/recomendaciones`

### `GET /api/recomendaciones?sku=&tienda=&excluir=`

| Parámetro | Obligatorio | Qué es |
|---|---|---|
| `sku` | sí | Producto ancla: lo que el cliente ya pidió |
| `tienda` | sí | Sucursal. **Aquí sí cambia el resultado** |
| `excluir` | no | SKUs ya en el ticket, separados por coma |

```bash
curl "http://localhost:8000/api/recomendaciones?sku=SKU001&tienda=merida&excluir=SKU004"
```

```json
{ "sustituto": null,
  "complementos": [
    { "sku": "SKU002", "tipo": "complemento", "score": 1.0,
      "fuente": "historico",
      "justificacion": "Llévese la varilla de estaño, ya que en uno de los tres tickets de este soplete se la han llevado junto.",
      "soporte": 1, "confianza": 0.3333, "lift": 7.0 } ] }
```

- **`sustituto`** — «mejor para esta plaza». Uno o `null`. Mismo trabajo, mejor
  material para el clima de la zona.
- **`complementos`** — «para terminar el trabajo». Hasta seis.
- **`fuente`** — `historico` (sale de tickets reales), `atributos` (del tipo de
  producto y el clima) o `manual` (lo puso una persona). **Se expone a
  propósito**: el vendedor tiene derecho a saber si la sugerencia se apoya en
  ventas o en criterio.
- **`soporte` / `confianza` / `lift`** — solo vienen si `fuente` es `historico`;
  por atributos no hay tickets que citar, y son `null`.
- **`justificacion`** — la frase que el vendedor puede repetirle al cliente.

**Filtros duros, no penalizaciones.** Nunca sale nada agotado, dado de baja,
bloqueado por el negocio ni presente en `excluir`. Un producto sin existencia no
es una mala sugerencia: es una imposible.

**`excluir` va en la query y esto es un `GET`.** Es una lectura, sin efectos, y
tiene que poder repetirse y cachearse. Meter el ticket en un cuerpo obligaría a
`POST` y mentiría sobre la semántica.

→ `404` si el SKU o la tienda no existen. → `422` si falta `sku` o `tienda`.

---

## 6. Relaciones y pesos

### `GET /api/relaciones?tipo=&fuente=`

El catálogo auditable de todo lo que el sistema sabe sugerir, con su evidencia.
**Es la misma tabla que consulta el mostrador**, no un informe aparte: lo que se
bloquea aquí cambia lo que se ofrece al cliente sin reiniciar nada.

`tipo`: `complemento` | `sustituto` · `fuente`: `historico` | `atributos` | `manual`

```json
{ "id": 10, "sku_origen": "SKU002", "sku_destino": "SKU004",
  "tipo": "complemento", "fuente": "historico", "score": 1.0,
  "soporte": 2, "confianza": 1.0, "lift": 14.0,
  "justificacion": "Se llevaron juntos en 2 de los 2 tickets con este producto.",
  "justificacion_ia": "Se han llevado ambos productos juntos en los 2 tickets registrados.",
  "estado": "activa", "peso_manual": null,
  "nombre_origen": "Varilla de soldar estaño 60/40",
  "nombre_destino": "Cartucho de gas MAPP",
  "stock_destino": 30, "activo_destino": true }
```

Los cuatro últimos campos son **desnormalización deliberada**: sin ellos la
pantalla tendría que pedir el catálogo entero y cruzarlo en el cliente para
poder escribir un nombre y saber si hay existencia.

`justificacion` y `justificacion_ia` van **separadas** para poder revertir al
texto de plantilla, auditar qué escribió la máquina, y limpiarla sola cuando la
plantilla cambia — señal de que los números que el LLM redactó ya no son ciertos.

### `PATCH /api/relaciones/{id}` → `200`

```json
{ "estado": "bloqueada" }
```

| Campo | Valores | Efecto |
|---|---|---|
| `estado` | `activa`, `bloqueada`, `fijada` | `bloqueada` no se ofrece nunca más. `fijada` se ofrece siempre primero |
| `peso_manual` | `0` … `10`, o `null` | Sustituye al puntaje calculado. `null` devuelve la relación a lo que diga el algoritmo |

**La decisión sobrevive a reconstruir las reglas.** El `score` lo calcula la
máquina y se recalcula; `estado` y `peso_manual` los pone una persona y
reconstruir no los pisa. Si no fuera así, el panel sería papel mojado.

Responde **exactamente la misma forma que el listado**, para que el cliente no
tenga que volver a pedirlo ni mantener dos representaciones de lo mismo.

→ `404` si el id no existe. → `422` con un `estado` fuera de los tres, o un peso
negativo o desproporcionado.

### `GET /api/config/pesos` → `{"historico": 0.7, "atributos": 1.0, "manual": 1.5}`

Cuánto pesa cada fuente al mezclar. `0` apaga una fuente; `1` es su peso natural.

### `PUT /api/config/pesos` → `200`

```json
{ "pesos": { "historico": 0.7, "atributos": 1.0 } }
```

**`PUT` y no `PATCH`**: son dos o tres números que se ajustan juntos y significan
algo *en relación entre sí*. Mandarlos de uno en uno dejaría estados intermedios
sin sentido —un instante con el histórico al máximo y los atributos sin bajar—.

Es un **mapa abierto** `fuente → peso`, no una lista de campos fijos, porque el
recomendador está declarado con el patrón Strategy: añadir una fuente nueva
(temporada, promociones) es añadir una clase, y esta configuración tiene que
admitirla sin cambiar el contrato ni migrar la tabla.

**Validación** — la tabla tiene `CHECK (peso >= 0)`, y sin acotar aquí un peso
negativo pasaba la validación y reventaba contra la base **con un `500`**, que es
mentir: el dato es inválido, no el servidor. Ahora:

| Regla | Motivo |
|---|---|
| `0 ≤ peso ≤ 10` | El tope no es técnico sino de sentido: por encima de 10 una fuente aplasta a la otra y el híbrido deja de serlo |
| Nombre `^[a-z][a-z_]{2,29}$` | Un dedazo crearía una fila de configuración que nadie va a leer nunca |
| Al menos una fuente | Un `PUT` con `{}` no significa nada |

---

## 7. Diagnóstico — `/api/diagnostico`

### `GET /api/diagnostico?tienda=`

**La única ruta que responde algo que nadie preguntó.** El resto de la API
contesta peticiones; ésta le dice a la sucursal lo que no sabe que le pasa.

```json
{ "tienda": "merida", "nombre": "Mérida", "perfil": "costero_salino",
  "tickets_en_la_plaza": 0, "tickets_en_la_cadena": 42, "productos_activos": 28,
  "hallazgos": [
    { "clave": "plaza_sin_historial", "nivel": "alerta",
      "titulo": "Mérida no tiene ni un ticket registrado",
      "detalle": "De los 42 tickets del histórico, ninguno es de esta sucursal…",
      "accion": "Cobra desde el mostrador o carga el histórico de esta tienda…",
      "total": 0, "productos": [] } ] }
```

| Hallazgo | Cómo se deriva |
|---|---|
| `plaza_sin_historial` | 0 tickets de esa tienda |
| `nunca_vendido` | 0 líneas de venta en toda la cadena |
| `sin_venta_en_la_plaza` | Se vende en otras tiendas y aquí no |
| `sin_existencia` | `stock = 0` y activo |
| `por_agotarse` | `stock ≤ 5` |
| `sin_recambio_para_la_plaza` | Adecuación al perfil < 0.5 **y** sin sustituto que sirva aquí |
| `sin_nada_que_ofrecer` | No aparece como origen de ninguna relación |
| `promocion_con_respaldo` | Par histórico con más soporte, ambos con existencia |

- **`nivel`** es `alerta`, `aviso` u `oportunidad`, y es un tipo cerrado: el panel
  pinta por nivel, y un valor inventado daría una tarjeta sin color en vez de un
  error.
- **`total` vs `productos`** — `total` son los afectados; `productos` trae solo
  los seis primeros. Un panel es una ayuda para decidir, no un inventario.
- **`accion`** — qué hacer. Un diagnóstico sin qué-hacer solo genera ansiedad y a
  la tercera vez se ignora.

Nada de esto es un caso especial escrito a mano: si Mérida sale distinta es
porque no tiene tickets, y **el aviso desaparece solo** en cuanto los tenga. Un
test lo comprueba cobrando ahí.

→ `404` si la tienda no existe. → `422` si falta `tienda`.

---

## 8. Sucursales — `/api/tiendas`

### `GET /api/tiendas`

**La primera llamada de la interfaz**: sin ella no se sabe en qué sucursal se
está, y `tienda` es obligatorio en casi todo lo demás.

```json
[ { "id": "cdmx", "nombre": "CDMX",
    "perfil": "interior_urbano", "acento": "#6B7280" } ]
```

- **`id`** es un slug ASCII (`cancun`, no `Cancún`). `sales.csv` trae acentos;
  arrastrarlos a ids, URLs y joins es una fuente segura de bugs de encoding.
- **`nombre`** lleva los acentos y es solo para mostrar.
- **`perfil`** —`costero_salino`, `sol_directo_seco`, `interior_urbano`,
  `taller_metalmecanico`— es lo que hace que el mismo producto reciba distinta
  sugerencia en Cancún y en Chihuahua. **Es lo que resuelve el arranque en frío
  de Mérida**: no depende del histórico.
- **`acento`** es el color con que se pinta la interfaz en esa plaza. No es
  decoración: evita cobrar en la sucursal equivocada.

---

## 9. Estado — `/` y `/api/salud`

### `GET /` → HTML

La única respuesta no-JSON del proyecto. **La raíz la abre una persona en un
navegador**, no un cliente HTTP: un `404` no le dice si la API arrancó bien, y
una página sí, además de llevarla a `/docs`.

### `GET /api/salud` → `200`

Lo mismo para una máquina.

```json
{ "estado": "listo", "version": "0.1.0",
  "base_de_datos": "D:\\...\\backend\\ferreteria.db",
  "origenes_cors": ["http://localhost:3000"],
  "contenido": { "tiendas": 5, "productos_activos": 28, "tickets": 42,
                 "relaciones": 151, "relaciones_redactadas_por_ia": 151 } }
```

`estado` vale `listo`, `base vacia` (falta correr el seed) o `sin base de datos`
(el archivo no existe o no tiene tablas). En los dos últimos casos `contenido`
es `null`.

Los conteos van **anidados** bajo `contenido` y no sueltos en la raíz: al lado de
`version: "0.1.0"`, un `productos: 28` no deja claro si son 28 productos o el
producto número 28. Agrupados se leen como lo que son.

`origenes_cors` responde la pregunta que más se hace quien clona el repositorio y
ve la interfaz en blanco: **desde qué origen acepta peticiones esta API**.

El mismo dato alimenta el banner de arranque de `uvicorn`, la portada y esta
ruta, desde una sola función. Si el banner dijera 28 productos y la portada otra
cosa, el dato dejaría de servir para diagnosticar nada.

---

## 10. Qué es `additionalProp1`

Aparece en `/docs`, en `/api/config/pesos`:

```json
{ "pesos": { "additionalProp1": 0 } }
```

**No es un campo.** Es un relleno que inventa Swagger UI.

Cuando un campo se declara como un **mapa abierto** —`dict[str, float]`, «un
objeto cuyas claves no sé de antemano, y cuyos valores son números»—, OpenAPI lo
describe así:

```json
{ "type": "object", "additionalProperties": { "type": "number" } }
```

Ese `additionalProperties` significa «cualquier clave vale». Como Swagger tiene
que enseñar *algo* en el ejemplo y no hay ninguna clave concreta que enseñar, se
inventa `additionalProp1`, `additionalProp2`, `additionalProp3`. **Si lo mandas
tal cual, creas una fuente llamada literalmente `additionalProp1`.**

Lo correcto es mandar las claves reales:

```json
{ "pesos": { "historico": 0.7, "atributos": 1.0 } }
```

**Por qué se dejó como mapa abierto** en vez de un modelo con tres campos fijos:
las fuentes son extensibles por diseño (Strategy). Fijarlas en el esquema
obligaría a tocar el contrato de la API cada vez que se añade una.

**Y qué se hizo para que el ejemplo no engañe:** el esquema declara un `example`
con las fuentes reales, así que `/docs` ahora muestra `historico` y `atributos`
en vez del relleno. Además el nombre de la fuente está validado
(`^[a-z][a-z_]{2,29}$`), así que un `additionalProp1` copiado por descuido
responde `422` en lugar de crear basura en la configuración.

> El mismo relleno aparecía en `/api/tiendas` y en `/api/salud`, que devolvían
> `dict` sin tipar. Ahora las dos tienen modelo, y `/docs` muestra sus campos
> reales.

---

## 11. Decisiones REST y por qué

| Decisión | Por qué |
|---|---|
| `PATCH` y no `PUT` para productos | La edición del catálogo es parcial: precio y existencia. Un `PUT` obligaría a mandar el recurso completo y a arriesgar pisar campos con valores por defecto |
| `PUT` y no `PATCH` para pesos | Al revés: son tres números que solo significan algo juntos |
| `DELETE` → `204` y borrado **lógico** | `ventas` y `movimientos_inventario` referencian el SKU; un borrado real rompería la trazabilidad. `204` porque no hay cuerpo que devolver |
| `DELETE` idempotente | Repetirlo no falla. El efecto buscado ya se cumplió |
| `Idempotency-Key` en **cabecera** | Es metadato de transporte, no parte del ticket |
| `excluir` como query param | La recomendación es una lectura: tiene que ser `GET`, repetible y cacheable |
| El error de stock lleva `sku` y `disponible` | El mostrador necesita el número, no un texto que tendría que parsear |
| Un `exception_handler` central | Traduce excepciones de dominio a códigos HTTP en un solo sitio. Es lo que permite que los servicios **no importen FastAPI** y se puedan probar sin levantar el servidor |
| Endpoints `def` y no `async def` | `sqlite3` es bloqueante: con `async def` bloquearía el event loop y el test de concurrencia dejaría de medir lo que dice medir |
| Sin versionado (`/v1/`) | No hay ningún consumidor externo al que romperle nada. Añadirlo ahora sería ceremonia |
| Sin paginación | 28 productos y 151 relaciones. Paginar aquí sería resolver un problema que no existe. Con un catálogo real, `GET /api/productos` y `GET /api/relaciones` serían las dos que la necesitarían |

---

## 12. Cómo probar todo esto

**Con la documentación interactiva** — `http://localhost:8000/docs`, botón
*Try it out* en cualquier ruta. Cada operación trae su descripción, sus
parámetros explicados y los códigos de error que puede devolver.

**Con la batería automática:**

```bash
cd backend
pytest -v tests/test_contrato_api.py    # el contrato completo, ruta por ruta
pytest -v                               # 67 tests, incluidos los 50 hilos
```

`test_contrato_api.py` fija el código de estado de **cada** ruta y la forma
exacta del JSON. Si alguien cambia un `404` por un `200`, o convierte un
booleano en entero, se rompe ahí antes de llegar a la interfaz.

**A mano, los tres casos que más cuesta creer:**

```bash
# 1. No se puede sobrevender: pide más de lo que hay
curl -X POST http://localhost:8000/api/compras -H "Content-Type: application/json" \
     -d '{"tienda":"cdmx","items":[{"sku":"SKU027","cantidad":999}]}'
# → 409  {"detail":"...Quedan 8.","sku":"SKU027","disponible":8}

# 2. Idempotencia: la misma clave dos veces no descuenta dos veces
curl -X POST http://localhost:8000/api/compras -H "Content-Type: application/json" \
     -H "Idempotency-Key: prueba-1" \
     -d '{"tienda":"cdmx","items":[{"sku":"SKU001","cantidad":1}]}'
# repite el mismo comando → mismo ticket_id, "repetida": true, mismo stock_restante

# 3. Mérida recomienda sin tener una sola venta
curl "http://localhost:8000/api/recomendaciones?sku=SKU010&tienda=merida"
```
