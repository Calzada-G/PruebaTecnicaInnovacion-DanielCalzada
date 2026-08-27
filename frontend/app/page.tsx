"use client";

import { useEffect, useMemo, useState } from "react";
import { PackageX, Sparkles } from "lucide-react";
import { BuscadorProducto } from "../componentes/BuscadorProducto";
import { EsperaHerramientas } from "../componentes/EsperaHerramientas";
import { BloqueRecomendacion } from "../componentes/BloqueRecomendacion";
import { ProductoTile } from "../componentes/ProductoTile";
import { Ticket } from "../componentes/Ticket";
import { useCompra } from "../hooks/useCompra";
import { useProducto, useProductos } from "../hooks/useProductos";
import { useRecomendaciones } from "../hooks/useRecomendaciones";
import { ErrorApi, type Producto } from "../lib/api";
import { useAvisos } from "../lib/notificaciones";
import { useTicket } from "../lib/ticket-context";
import { useTienda } from "../lib/tienda-context";
import { precio } from "../lib/visual";

function saludo(): string {
  const h = new Date().getHours();
  if (h < 12) return "Buenos días";
  if (h < 20) return "Buenas tardes";
  return "Buenas noches";
}

/**
 * El saludo se calcula despues de montar, no durante el render.
 *
 * Next prerenderiza tambien los componentes de cliente, asi que la hora del
 * servidor y la del navegador pueden no coincidir (otra zona horaria, o
 * simplemente cruzar la hora en punto) y React marcaria desajuste de
 * hidratacion. Partir de un saludo neutro evita el problema de raiz.
 */
function useSaludo(): string {
  const [momento, setMomento] = useState("Hola");
  useEffect(() => setMomento(saludo()), []);
  return momento;
}

export default function Mostrador() {
  const { tiendaId, tienda } = useTienda();
  const { notificar } = useAvisos();
  const ticket = useTicket();
  const momento = useSaludo();
  const [consulta, setConsulta] = useState("");
  const [sku, setSku] = useState<string | null>(null);

  const { data: productos = [], isLoading } = useProductos(consulta, tiendaId);
  const { data: seleccionado } = useProducto(sku);
  const excluir = useMemo(() => ticket.lineas.map((l) => l.sku), [ticket.lineas]);
  const { data: recomendacion } = useRecomendaciones(sku, tiendaId, excluir);
  const compra = useCompra();

  // El catalogo completo alimenta las tarjetas: un candidato puede no estar en
  // los resultados de la busqueda actual.
  const { data: catalogoCompleto = [] } = useProductos("", tiendaId);
  const catalogo = useMemo(() => {
    const mapa = new Map<string, Producto>();
    for (const p of [...catalogoCompleto, ...productos]) mapa.set(p.sku, p);
    return mapa;
  }, [catalogoCompleto, productos]);

  function agregar(skuAgregar: string) {
    const producto = catalogo.get(skuAgregar);
    if (producto) ticket.agregar(producto);
  }

  /** Cambia el ancla por el sustituto, y tambien en el ticket si ya estaba. */
  function sustituir(skuSustituto: string) {
    const anterior = sku;
    const nuevo = catalogo.get(skuSustituto);
    setSku(skuSustituto);
    if (anterior && ticket.lineas.some((l) => l.sku === anterior)) {
      ticket.quitar(anterior);
      agregar(skuSustituto);
    } else if (nuevo) {
      notificar(
        "info",
        "Cambiado a la opción de esta plaza",
        `${nuevo.nombre} — ${nuevo.material}`,
      );
    }
  }

  async function cobrar() {
    ticket.registrarError(null);
    try {
      const respuesta = await compra.mutateAsync({
        tienda: tiendaId,
        items: ticket.lineas.map((l) => ({ sku: l.sku, cantidad: l.cantidad })),
      });
      ticket.registrarCobro(respuesta);
      notificar(
        "exito",
        `Ticket ${respuesta.ticket_id} cobrado`,
        `${precio(respuesta.total)} · inventario descontado en ${tienda?.nombre ?? tiendaId}.`,
      );
    } catch (excepcion) {
      const mensaje =
        excepcion instanceof ErrorApi
          ? excepcion.message
          : "No se pudo cobrar. Intenta de nuevo.";
      ticket.registrarError(mensaje);
      notificar("error", "No se pudo cobrar", mensaje);
    }
  }

  const agotado = seleccionado?.stock === 0;
  const pocas = !!seleccionado && seleccionado.stock > 0 && seleccionado.stock <= 5;

  // Las tres columnas ocupan exactamente el alto disponible y cada una decide
  // que scrollea dentro. Con alturas calculadas a mano quedaba un hueco muerto
  // bajo la lista y bajo el ticket que cambiaba con cada tamano de ventana.
  return (
    <div className="grid gap-3 lg:h-full lg:grid-cols-[300px_minmax(0,1fr)_300px] lg:grid-rows-[minmax(0,1fr)]">
      <div className="h-[55vh] min-h-[18rem] lg:h-auto lg:min-h-0">
        <BuscadorProducto
          consulta={consulta}
          onConsulta={setConsulta}
          productos={productos}
          skuSeleccionado={sku}
          onSeleccionar={setSku}
          cargando={isLoading}
        />
      </div>

      <div className="flex min-w-0 flex-col gap-3 lg:min-h-0 lg:overflow-y-auto">
        {!seleccionado && (
          <section className="tarjeta aparece p-5">
            <h1 className="text-lg font-semibold">
              {momento}. Estás en la sucursal{" "}
              <span style={{ color: "var(--color-acento)" }}>
                {tienda?.nombre ?? "…"}
              </span>
              .
            </h1>
            <p className="mt-1 max-w-2xl text-sm text-acero">
              Busca lo que pide el cliente y el sistema te dirá{" "}
              <strong className="font-medium text-tinta">
                qué más ofrecerle
              </strong>{" "}
              y{" "}
              <strong className="font-medium text-tinta">
                si hay una versión mejor para esta plaza
              </strong>
              . El inventario es compartido entre las 5 sucursales y se descuenta
              al cobrar.
            </p>

            <div className="mt-4 grid gap-2 sm:grid-cols-3">
              {[
                {
                  titulo: "1 · Busca",
                  texto: "Por nombre, material o uso. Pulsa / para ir al buscador.",
                },
                {
                  titulo: "2 · Revisa las sugerencias",
                  texto:
                    "Cada una sale de las ventas o del tipo de producto.",
                },
                {
                  titulo: "3 · Cobra",
                  texto: "El stock baja al instante y nunca se vende de más.",
                },
              ].map((paso) => (
                <div
                  key={paso.titulo}
                  className="rounded-[var(--radio)] border border-linea p-2.5"
                >
                  <p
                    className="text-xs font-semibold"
                    style={{ color: "var(--color-acento)" }}
                  >
                    {paso.titulo}
                  </p>
                  <p className="mt-0.5 text-xs leading-snug text-acero">
                    {paso.texto}
                  </p>
                </div>
              ))}
            </div>

            <p className="mt-4 text-xs text-acero">
              El ticket se conserva aunque cambies de interaz. Solo se vacía al cambiar de sucursal.
            </p>
          </section>
        )}

        {!seleccionado && <EsperaHerramientas />}

        {seleccionado && (
          <>
            <section className="tarjeta aparece p-3">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0 flex-1">
                  <ProductoTile
                    sku={seleccionado.sku}
                    nombre={seleccionado.nombre}
                    categoria={seleccionado.categoria}
                    material={seleccionado.material}
                    uso={seleccionado.uso_recomendado}
                  />
                  <p className="recorta-2 mt-2 max-w-xl text-xs text-acero">
                    {seleccionado.descripcion} · Recomendado para{" "}
                    {seleccionado.uso_recomendado}.
                  </p>
                </div>

                <div className="flex shrink-0 items-center gap-3">
                  <div className="text-right">
                    <div className="cifra text-xl font-medium leading-none">
                      {precio(seleccionado.precio)}
                    </div>
                    <div
                      className="cifra mt-1 text-xs"
                      style={{
                        color: agotado
                          ? "var(--color-error)"
                          : pocas
                            ? "var(--color-alerta)"
                            : "var(--color-acero)",
                      }}
                    >
                      {agotado ? "sin existencia" : `${seleccionado.stock} pz`}
                    </div>
                  </div>
                  <button
                    onClick={() => agregar(seleccionado.sku)}
                    disabled={agotado}
                    className="boton boton-primario px-4 py-2.5"
                  >
                    Agregar al ticket
                  </button>
                </div>
              </div>

              {agotado && (
                <p
                  className="mt-2 flex items-center gap-1.5 rounded-[var(--radio)] px-2.5 py-1.5 text-xs"
                  style={{ background: "#fef2f2", color: "var(--color-error)" }}
                >
                  <PackageX size={14} aria-hidden />
                  Agotado. No se puede vender ni recomendar.
                </p>
              )}
            </section>

            <BloqueRecomendacion
              titulo="Mejor para esta plaza"
              descripcion={
                tienda
                  ? `Aguanta mejor las condiciones de ${tienda.nombre}`
                  : "Más adecuado para esta sucursal"
              }
              candidatos={recomendacion?.sustituto ? [recomendacion.sustituto] : []}
              catalogo={catalogo}
              etiquetaAccion="Sustituir"
              onAccion={sustituir}
              vacio="Este producto ya es el adecuado para esta plaza."
              destacado
            />

            <BloqueRecomendacion
              titulo="Para terminar el trabajo"
              descripcion="Lo que suele hacer falta junto con este producto"
              candidatos={recomendacion?.complementos ?? []}
              catalogo={catalogo}
              etiquetaAccion="Agregar"
              onAccion={agregar}
              vacio="Sin complementos con existencia ahora mismo."
            />

            <p className="flex items-center gap-1.5 text-[11px] text-acero">
              <Sparkles size={12} aria-hidden />
              Solo se sugiere lo que hay en existencia y no está ya en el ticket.
            </p>
          </>
        )}
      </div>

      <div className="h-[55vh] min-h-[18rem] lg:h-auto lg:min-h-0">
        <Ticket
          lineas={ticket.lineas}
          onCantidad={ticket.cambiarCantidad}
          onQuitar={ticket.quitar}
          onCobrar={cobrar}
          cobrando={compra.isPending}
          error={ticket.error}
          ultimo={ticket.ultimo}
          nombreTienda={tienda?.nombre ?? ""}
        />
      </div>
    </div>
  );
}
