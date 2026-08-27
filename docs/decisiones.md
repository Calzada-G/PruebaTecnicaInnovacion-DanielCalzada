# Decisiones de diseño

Cada sección responde una pregunta que un evaluador haría en entrevista.

---

## 1. ¿Por qué el motor no son las reglas de asociación?

Porque los datos no dan para eso, y conviene decirlo con números:

| Hecho medido en `sales.csv` | Valor |
|---|---|
| Tickets | 42 |
| Líneas de venta | 89 |
| Pares co-ocurrentes distintos | 45 |
| **Pares que aparecen en más de un ticket** | **8** |
| Tiendas con historial | 4 de 5 (Mérida no aparece) |
| SKUs sin una sola venta | 1 (SKU027) |

Con 42 tickets, un lift de 14 sobre un soporte de 2 no es una señal: es ruido con
decimales. Montar el sistema sobre eso sería construir sobre arena y presentarlo
como cimiento.

**Decisión:** las reglas de asociación son **una fuente de evidencia auditable**;
el motor es la capa de atributos. Lo respalda la evaluación: sobre los 7 pares de
dominio que nunca co-ocurren, el histórico recupera **0/7** y los atributos
**6/7** (`docs/evaluacion.md`).

### Y aun así, el histórico no se tira

Cuando hay evidencia real, convence más que cualquier regla. Por eso:

- El score **no** es la confianza cruda sino su **límite inferior de Wilson**
  sobre `soporte(ancla)`. Una regla vista 2 de 2 veces puntúa 1.000; una vista 1
  de 3 cae a ~0.06. Castiga la muestra corta sin inventar significancia.
- Soporte, confianza y lift se guardan y se muestran en el panel aunque el
  ranking no los use tal cual: el negocio tiene que poder auditar la evidencia.
- Si las dos fuentes proponen el mismo par, eso es **corroboración**: se toma el
  puntaje mayor pero se muestra el candidato con tickets detrás, porque al
  cliente lo convence *"se llevaron juntos en 2 de 3 tickets"*, no *"por
  atributos"*.

---

## 2. ¿Cómo se resuelven los dos arranques en frío?

Son dos y son deliberados en los datos:

**Mérida no existe en `sales.csv`.** Ninguna regla de co-ocurrencia puede hablar
de esa plaza. Su perfil sí: `costero_salino`, cruzado con el `uso_recomendado` de
cada producto, basta para proponer inoxidable 316 sobre acero al carbón.

> ⚠️ El perfil de Mérida está **asignado por conocimiento externo** (península de
> Yucatán, clima marino), no derivado de datos. Es un supuesto declarado, no un
> hallazgo. Está anotado como tal en `app/seed.py` y aquí.

**SKU027 (regulador MAPP) no se ha vendido nunca.** Sale como complemento del
soplete por su *rol* (accesorio de la actividad `soldadura`), no por historial.

La clasificación de `actividad`, `rol` y `ambiente` se **deriva** de `categoria`,
`uso_recomendado` y `material`, no de una tabla de SKUs. Un producto dado de alta
hoy queda clasificado sin tocar código.

Dos trampas del texto que costaron un bug cada una:

- `"interior y exterior protegido de la luz solar"` (tubo PVC) **contiene la
  palabra "solar"**. Si se comprueba `solar` antes que `protegido`, el PVC de
  interior queda clasificado como apto para intemperie — justo el error que este
  sistema existe para evitar.
- `"soldadura eléctrica y electrónica"` (varilla de estaño) **contiene
  "electric"**. Si se comprueba la actividad eléctrica antes que la de soldadura,
  la varilla se desconecta del soplete.

---

## 3. ¿Por qué SQLite a pelo y no un ORM?

Porque el requisito crítico es **control exacto de la transacción**, y ahí un ORM
añade manejo de sesiones y threading que hay que dominar para defenderlo, sin
aportar nada a cambio.

La garantía de no sobreventa vive en una sola línea:

```sql
UPDATE productos SET stock = stock - ?
 WHERE sku = ? AND activo = 1 AND stock >= ?
```

La validación está **en el `WHERE`**. Está prohibido un `SELECT stock` previo
decidido en Python: entre leer y escribir cabe otra transacción. Si
`rowcount != 1`, se aborta el ticket entero.

Alrededor: `BEGIN IMMEDIATE` (toma el candado al abrir, no en el primer UPDATE),
`WAL`, `busy_timeout=5000`, `CHECK (stock >= 0)` como última defensa, y endpoints
con `def` síncrono — **nunca `async def`**, porque `sqlite3` es bloqueante y con
`async def` se bloquearía el event loop, con lo que el test de concurrencia
dejaría de medir lo que dice medir.

**Verificado:** 50 hilos comprando 1 unidad contra stock 8 → exactamente 8 éxitos
y stock final 0.

### Clasificar el fallo sin romper la garantía

Un `rowcount = 0` colapsa tres causas indistinguibles desde SQL. Devolver siempre
409 hacía que un SKU mal tecleado respondiera *"no hay suficiente inventario"*.
Ahora se consulta el producto **después** del fallo, solo para redactar la
verdad: 404 inexistente, 400 dado de baja, 409 sin stock. La decisión de vender
la sigue tomando el `WHERE`.

---

## 4. ¿Dónde se garantiza que no se recomienda algo agotado?

En **un solo punto**: `ranking.mezclar`. Que sea uno solo es deliberado — el
requisito se cumple o se rompe ahí, y así hay un único sitio que auditar y que
testear. Los filtros son **duros**, no ponderaciones: lo que no pasa no existe,
por muy alto que puntúe.

Se filtra: `stock = 0`, `activo = 0`, el propio ancla, lo ya presente en el
ticket (`excluir`), lo `bloqueada` por el negocio, y **la misma familia**.

Lo último fue un bug real: SKU005 y SKU006 co-ocurren en T036, así que el
histórico ofrecía el tornillo galvanizado como *complemento* del de carbón. En
Mérida el sistema aconsejaba dos cosas contradictorias a la vez: *"cámbialo por
el inoxidable"* y *"llévate también el galvanizado"*. `AtributosStrategy` ya lo
excluía, pero lo hacía dentro de una fuente; la regla es de negocio y vale para
todas.

---

## 5. ¿Por qué el LLM no está en el endpoint?

El PDF sugiere usar APIs gratuitas de IA. Se usa **Gemini, pero en batch**, y el
LLM **no decide qué se recomienda ni en qué orden: solo redacta**.

Tres razones que pesan más que la comodidad de llamarlo en línea:

1. **Latencia.** El usuario es un vendedor con un cliente enfrente. Meter una
   llamada de red en esa pantalla empeora justo lo que se quiere mejorar.
2. **Arranque.** Ataría la POC a que el evaluador tenga API key. Sin clave el
   script avisa, no escribe nada, y **todo el sistema funciona igual** con las
   justificaciones de plantilla.
3. **Determinismo.** El ranking se evalúa offline y debe dar el mismo número dos
   veces. Un LLM en el camino de servir rompe eso.

El texto va a una columna aparte (`justificacion_ia`), así que se puede revertir,
auditar y editar desde el panel de Relaciones. Se limpia sola cuando cambia la
plantilla: señal de que los números que el LLM redactó ya no son ciertos.

### La búsqueda del modelo: tres iteraciones contra la API real

Esto no salió a la primera y el recorrido es parte de la decisión.

**Iteración 1 — `gemini-2.0-flash` → 404.**
Era el default que puse de memoria. Contra la API actual **ya no existe**. Al
listar los modelos disponibles con la clave aparecieron `gemini-3.7-flash`,
`gemini-3.1-flash-lite` y compañía: bastante más nuevos que el que había fijado.

**Iteración 2 — `gemini-flash-latest` → 429 constantes.**
Alias que Google mantiene apuntando al flash estable vigente. Elegido para no
caducar. Pero resuelve a **3.7 Flash**, el modelo puntero, y en el tier gratuito
eso significa:

| Modelo | Peticiones/min | Peticiones/día |
|---|---:|---:|
| Gemini 3.7 Flash (`gemini-flash-latest`) | 5 | **20** |
| Gemini 3.1 Flash Lite | 15 | **500** |

Son **151 relaciones** que redactar en lotes de 20 → 8 peticiones por pasada
completa. Con 20 al día compartidas con cualquier otra prueba, el script se
pasaba el rato reintentando `429` y escribía **40 por pasada**.

**Iteración 3 — `gemini-3.1-flash-lite` → 151/151 en ocho lotes, cero reintentos.**

**El criterio de elección fue la cuota, no la capacidad.** Reescribir una frase
de una línea con un límite de 140 caracteres no necesita el modelo más capaz del
catálogo; necesita poder ejecutarse 8 veces seguidas. Un modelo *lite* con 25× la
cuota diaria es estrictamente mejor para esta tarea, y la calidad del resultado lo
confirma:

> plantilla → `Para soldadura: completa el equipo.`
> LLM → `Llévese el regulador para completar su equipo de soldadura.`

**Coste asumido:** fijar una versión concreta caduca, como le pasó a
`gemini-2.0-flash`. Se asume a conciencia porque el fallo es benigno: el script lo
dice, no escribe nada, y el sistema sigue con las plantillas. La alternativa
(`-latest`, que no caduca) hacía que el script no terminara nunca su trabajo, que
es un fallo peor.

### Un bug de seguridad que solo apareció con clave real

La clave viajaba como `?key=...`. `httpx` incluye **la URL completa** en el texto
de sus excepciones, así que el primer `404` impreso en consola **filtró la
credencial**. Corregido: va en la cabecera `x-goog-api-key`, y además se sanea el
mensaje de error por si apareciera por otra vía.

> La clave de pruebas llegó a estar en `backend/.env.example`, que **sí se
> commitea**. Se movió a `backend/.env` (ignorado) antes de cualquier commit; se
> verificó que no entró en el historial.

---

## 6. ¿Cómo se sabe que las recomendaciones son buenas?

Tres comprobaciones, porque ninguna basta sola. Detalle en `docs/evaluacion.md`.

**a) Leave-one-out sobre las 42 canastas** — hit-rate@3 **0.472** frente a 0.337
del mejor baseline. Dos decisiones sostienen que el número sea honesto:

- **Sin fuga de datos:** en cada pliegue las reglas se reconstruyen **ocultando el
  ticket completo** que se está midiendo. Construirlas una vez desde toda la base
  inflaría el acierto porque cada regla habría visto la respuesta.
- **Base propia** sembrada desde los CSV, para que el resultado no cambie si
  alguien compró en la UI.

Se reporta el intervalo de Wilson y **se declara ancho**: con n=42 no da para
proclamar un ganador, y presentarlo como si diera sería presentar ruido.

**b) Conjunto dorado de 25 pares de dominio.** La primera versión fue una trampa
involuntaria: elegí pares que ya estaban en los datos, el histórico "recuperaba"
18/20 y no demostraba nada. Rehecho con 7 pares verificados que **nunca**
co-ocurren → histórico **0/7**, atributos **6/7**.

El par que falla (`varilla de plata → cartucho`, queda en posición 7) **se
documenta en vez de ajustar los pesos para acertarlo**: sobreajustar a un conjunto
escrito por el propio autor del sistema no sería evaluar.

**c) Caso Mérida** — recomendaciones coherentes con perfil costero, con cero
historial.

---

## 7. Decisiones menores con su motivo

| Decisión | Motivo |
|---|---|
| `tiendas.id` slug ASCII (`cancun`) y `nombre` con acento (`Cancún`) | `sales.csv` trae acentos; arrastrarlos a ids, URLs y joins es una fuente de bugs de encoding |
| `?tienda=` en el catálogo **ordena**, no filtra | El inventario es compartido: la tienda no puede cambiar el stock, pero sí qué encuentra antes el vendedor |
| Líneas repetidas del mismo SKU se **suman** antes de descontar | Dos líneas de 5 contra stock 8 deben fallar como una de 10, no colar 5 y luego 5 |
| Tope de 6 complementos, no 3 | Los consumibles de una actividad puntúan casi igual; con un tope corto llenan la lista de casi-duplicados (dos varillas) y dejan fuera el accesorio y el EPP |
| `movimientos_inventario` append-only | Permite reconstruir el stock sumando deltas; un test comprueba que cuadra |
| El ticket se vacía al cambiar de tienda, y **solo** ahí | Un ticket pertenece a la plaza donde se cobra. Cambiar de vista no es cambiar de plaza: consultar un precio en el catálogo a media venta es lo normal, así que el ticket vive en el layout y sobrevive a la navegación |
| El diagnóstico de plaza se calcula en el backend | Tres de sus ocho hallazgos necesitan la tabla `ventas`, que la API no expone; calcularlo en el cliente obligaría a mandarle el histórico entero para deducir una frase |
| Un solo `QueryClient` por montaje, en `useState` | Evita que un remount comparta caché sin querer |
| El peso por fuente decide también un **corte de evidencia** | Medido: como simple multiplicador, los tres modos del panel daban el mismo conjunto de sugerencias en las 140 consultas. Un peso responde «cuál prefiero»; el negocio pregunta «cuánta evidencia exijo» |
| El corte es **relativo** al mejor candidato, no absoluto | Con un umbral fijo, Mérida —cero tickets— se quedaría en blanco en el modo exigente, que es justo el caso que el sistema debe cubrir |
| Los complementos **no** dependen de la plaza | Responden al trabajo del cliente, no al clima. Ordenarlos por ventas locales metería datos de la plaza en el orden y filtraría en la evaluación |
| El LLM analiza, no redacta | Reescribir justificaciones gasta una llamada por relación para cambiar cómo suena algo ya sabido. Una llamada que lee todo el sistema produce algo que no estaba |
| El análisis se cachea por **huella del estado** | Preguntar dos veces lo mismo devuelve lo mismo y no vale una llamada. La garantía vive en el servidor, no en el botón |
| `FAMILIAS` como constante | Honesto para 28 SKUs; **no escala** — en producción es una columna del maestro de productos |

---

## 8. Fuera de alcance, y cómo lo resolvería

**Autenticación y roles.** El PDF la marca opcional. En producción el panel de
Relaciones y el CRUD no pueden estar abiertos: OAuth2 con scopes `vendedor` /
`encargado`, y el selector de tienda derivado del usuario, no elegible a mano.

**`FAMILIAS` cableado.** Un alta nueva no entra en ninguna familia hasta que
alguien la añada al código. Se resuelve con una columna `familia` en `productos`,
editable desde el catálogo. No se hizo porque cambiaba el esquema acordado.

**Reconstruir relaciones tras un alta.** Las reglas se materializan con un script.
Un producto nuevo recibe complementos por atributos en el acto (se calculan en
vivo) pero no aparece en el panel hasta reconstruir. En producción: un disparador
tras el alta, o una tarea programada nocturna.

**La métrica que de verdad importa.** Subir ventas no se demuestra offline. Haría
un A/B en mostrador midiendo **tasa de aceptación de la sugerencia** y **ticket
promedio**, con el `fuente` de cada candidato como dimensión para saber qué capa
aporta. La evaluación offline sirve para no salir a producción a ciegas, no para
declarar victoria.

**Recomendación personalizada por cliente.** No hay identificador de cliente en
los datos. Con uno, la siguiente capa natural es filtrado colaborativo — que
seguiría necesitando la capa de atributos debajo para el arranque en frío.
