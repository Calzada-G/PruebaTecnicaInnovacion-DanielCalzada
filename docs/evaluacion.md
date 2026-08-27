# Evaluacion del recomendador

> Generado por `python scripts/evaluar.py`. Reproducible: base temporal
> sembrada desde los CSV y baseline aleatorio con semilla fija.

## 1. Leave-one-out sobre las canastas reales

- Canastas: **42 tickets**, todas de 2 o mas articulos.
- Instancias evaluadas: **89** (cada linea de venta ocultada una vez).
- Metricas: hit-rate@3 y MRR. Intervalo de Wilson al 95%.
- Las reglas de asociacion se reconstruyen **ocultando el ticket medido**,
  asi que ningun acierto viene de haber visto la respuesta.

| Recomendador | hit-rate@3 | IC 95% (Wilson) | MRR |
|---|---:|:---:|---:|
| **hibrido (este sistema)** | 0.472 (42/89) | [0.372, 0.575] | 0.330 |
| aleatorio con stock | 0.112 (10/89) | [0.062, 0.195] | 0.071 |
| mas vendido global | 0.112 (10/89) | [0.062, 0.195] | 0.052 |
| mas vendido en la tienda | 0.337 (30/89) | [0.247, 0.440] | 0.180 |
| misma categoria | 0.135 (12/89) | [0.079, 0.221] | 0.096 |

### Como leer esta tabla

**El intervalo de confianza es ancho y se solapa entre metodos.** Con 42
canastas no da para declarar un ganador estadisticamente significativo, y
presentarlo como si lo diera seria presentar ruido como metrica. Lo que la
tabla si sostiene es la direccion del efecto y, sobre todo, que el sistema
no es peor que las heuristicas triviales que ya podria aplicar el negocio.

La razon de fondo es estructural: solo 8 de los 45 pares co-ocurrentes
aparecen en mas de un ticket. Un test de canasta no puede premiar lo que
nunca se vendio junto, y justamente ahi es donde este sistema aporta. Por
eso la evaluacion sigue con dos comprobaciones cualitativas.

### Que cuesta y que da cada modo del panel

Los tres modos de la pantalla de Relaciones no son texto: cambian cuanta
evidencia se exige para ofrecer algo. Aqui esta el precio de cada uno,
medido sobre las mismas 89 instancias.

| Modo | hit-rate@3 | MRR | Sugerencias por producto |
|---|---:|---:|---:|
| solo lo comprobado | 0.326 (29/89) | 0.217 | 2.2 |
| equilibrado | 0.472 (42/89) | 0.330 | 3.4 |
| descubrir mas | 0.494 (44/89) | 0.335 | 4.5 |

**Exigir mas evidencia cuesta aciertos, y eso es correcto.** «Solo lo
comprobado» acierta menos porque ofrece menos: recorta la cola de
sugerencias deducidas, y en esa cola caia algun acierto. Es la decision
que el negocio toma conscientemente -precision antes que cobertura- y
por eso el panel la ofrece como un modo y no como un valor por defecto
escondido.

## 2. Conjunto dorado de dominio

20 pares que cualquier ferretero daria por obvios. Mide cobertura de
dominio, no popularidad: es donde se ve que aporta cada fuente.

| Par | historico | atributos | hibrido |
|---|:---:|:---:|:---:|
| soplete -> cartucho de gas | si | si | si |
| soplete -> regulador (*) | - | si | si |
| regulador -> cartucho de gas (*) | - | si | si |
| regulador -> soplete (*) | - | si | si |
| manguera -> regulador (*) | - | si | si |
| varilla de plata -> cartucho (*) | - | - | - |
| broca de concreto -> guantes (*) | - | si | si |
| soplete -> manguera de repuesto | si | si | si |
| soplete -> careta de soldar | si | si | si |
| soplete -> varilla de estano | si | si | si |
| soplete -> varilla de plata | si | si | si |
| cartucho -> varilla de aporte | si | si | si |
| taladro -> broca de concreto | si | si | si |
| taladro -> broca de metal | si | si | si |
| taladro -> guantes | si | si | si |
| tubo PVC -> cemento PVC | si | si | si |
| tubo CPVC -> cemento PVC | si | si | si |
| tubo PVC -> sellador | si | si | si |
| cemento PVC -> tubo | si | si | si |
| careta -> guantes | si | si | si |
| cable uso rudo -> grasa dielectrica | si | si | si |
| cable THHW -> grasa dielectrica (*) | - | si | si |
| lamina galvanizada -> anticorrosiva | si | si | si |
| lamina galvanizada -> tornillo galvanizado | si | si | si |
| lamina de carbon -> tornillo de carbon | si | si | si |
| **TOTAL** | **18/25** | **24/25** | **24/25** |

### Los 7 pares marcados (*): el argumento central

Son pares que **nunca co-ocurren en `sales.csv`**. Sobre ese subconjunto:

- solo historico: **0/7**  (no es un defecto del algoritmo, es imposible por construccion: no puede contar lo que nunca paso)
- solo atributos: **6/7**
- hibrido: **6/7**

El sistema falla 1 de ellos: varilla de plata -> cartucho (*). Es un complemento de segundo orden (la varilla necesita el soplete y el soplete necesita el gas) y queda en la posicion 7 por muy poco. **No se ajustaron los pesos para forzar el acierto**: seria sobreajustar a un conjunto escrito por el mismo autor del sistema.

Este es el motivo de que la capa de atributos sea el motor y las reglas de
asociacion la evidencia. Con 42 tickets el historico cubre lo que ya se
vendio junto; el catalogo de una ferreteria es mucho mas grande que eso.

## 3. Caso Merida: recomendar sin una sola venta

Merida no aparece en `sales.csv`. Ninguna regla de asociacion puede
hablar de esa plaza; el perfil costero si.

**SKU005 - Tornillo acero al carbón 1/4 (caja 100)**

- Mejor para esta plaza: `SKU007` Tornillo acero inoxidable 316 1/4 (caja 100) - acero inoxidable 316: resiste corrosion salina. El actual es para interior y esta plaza es costera y salina.
- Para terminar el trabajo: `SKU015` Pintura vinílica interior (historico)
- Para terminar el trabajo: `SKU021` Guantes de carnaza (atributos)
- Para terminar el trabajo: `SKU008` Lámina galvanizada calibre 24 (atributos)

**SKU010 - Tubo PVC cédula 40 3/4**

- Mejor para esta plaza: `SKU011` Tubo CPVC estabilizado UV 3/4 - CPVC estabilizado UV: resiste radiacion solar directa. El actual es para interior y esta plaza es costera y salina.
- Para terminar el trabajo: `SKU012` Cemento para PVC 250ml (historico)
- Para terminar el trabajo: `SKU013` Sellador de silicón (historico)

**SKU024 - Candado acero al carbón**

- Mejor para esta plaza: `SKU025` Candado acero inoxidable marino - acero inoxidable marino: resiste corrosion salina. El actual es para interior y esta plaza es costera y salina.
- Para terminar el trabajo: `SKU005` Tornillo acero al carbón 1/4 (caja 100) (historico)
- Para terminar el trabajo: `SKU022` Cable eléctrico calibre 12 rollo 100m (historico)

## 4. Limitaciones declaradas

- n=42 canastas: el intervalo es ancho. No se declara ganador.
- El leave-one-out mide complementos. El sustituto no cabe en esta prueba
  porque por definicion no aparece en la misma canasta; se valida con el
  conjunto dorado y el caso Merida.
- El conjunto dorado lo escribio quien construyo el sistema. Mide
  cobertura de dominio, no aceptacion del cliente.
- La medida que de verdad importa (subir ventas) solo se obtiene con un
  A/B en mostrador midiendo tasa de aceptacion y ticket promedio. Esta
  evaluacion offline sirve para no salir a produccion a ciegas.