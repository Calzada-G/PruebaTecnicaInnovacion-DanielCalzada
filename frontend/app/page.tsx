"use client";

import { useEffect, useMemo, useState } from "react";
import { BuscadorProducto } from "../componentes/BuscadorProducto";
import { BloqueRecomendacion } from "../componentes/BloqueRecomendacion";
import { ProductoTile } from "../componentes/ProductoTile";
import { Ticket, type LineaTicket } from "../componentes/Ticket";
import { useCompra } from "../hooks/useCompra";
import { useProducto, useProductos } from "../hooks/useProductos";
import { useRecomendaciones } from "../hooks/useRecomendaciones";
import { ErrorApi, type CompraRespuesta, type Producto } from "../lib/api";
import { useTienda } from "../lib/tienda-context";
import { precio } from "../lib/visual";

export default function Mostrador() {
  const { tiendaId, tienda } = useTienda();
  const [consulta, setConsulta] = useState("");
  const [sku, setSku] = useState<string | null>(null);
  const [lineas, setLineas] = useState<LineaTicket[]>([]);
  const [ultimo, setUltimo] = useState<CompraRespuesta | null>(null);
  const [error, setError] = useState<string | null>(null);

  const { data: productos = [], isLoading } = useProductos(consulta, tiendaId);
  const { data: seleccionado } = useProducto(sku);
  const excluir = useMemo(() => lineas.map((l) => l.sku), [lineas]);
  const { data: recomendacion } = useRecomendaciones(sku, tiendaId, excluir);
  const compra = useCompra();

  // Un ticket pertenece a una plaza: descuenta de su caja y se cobra ahi. Al
  // cambiar de tienda se vacia, en vez de arrastrar lineas a otra sucursal.
  useEffect(() => {
    setLineas([]);
    setUltimo(null);
    setError(null);
  }, [tiendaId]);

  // El catalogo completo alimenta las tarjetas de recomendacion: un candidato
  // puede no estar en los resultados de la busqueda actual.
  const { data: catalogoCompleto = [] } = useProductos("", tiendaId);
  const catalogo = useMemo(() => {
    const mapa = new Map<string, Producto>();
    for (const p of [...catalogoCompleto, ...productos]) mapa.set(p.sku, p);
    return mapa;
  }, [catalogoCompleto, productos]);

  function agregar(skuAgregar: string) {
    const producto = catalogo.get(skuAgregar);
    if (!producto || producto.stock === 0) return;
    setError(null);
    setUltimo(null);
    setLineas((actuales) => {
      const existente = actuales.find((l) => l.sku === skuAgregar);
      if (existente) {
        if (existente.cantidad >= producto.stock) return actuales;
        return actuales.map((l) =>
          l.sku === skuAgregar ? { ...l, cantidad: l.cantidad + 1 } : l,
        );
      }
      return [
        ...actuales,
        {
          sku: producto.sku,
          nombre: producto.nombre,
          precio: producto.precio,
          cantidad: 1,
          stock: producto.stock,
        },
      ];
    });
  }

  function cambiarCantidad(skuLinea: string, cantidad: number) {
    if (cantidad <= 0) return setLineas((a) => a.filter((l) => l.sku !== skuLinea));
    setLineas((a) =>
      a.map((l) =>
        l.sku === skuLinea ? { ...l, cantidad: Math.min(cantidad, l.stock) } : l,
      ),
    );
  }

  /** Cambia el ancla por el sustituto, y tambien en el ticket si ya estaba. */
  function sustituir(skuSustituto: string) {
    const anterior = sku;
    setSku(skuSustituto);
    if (anterior && lineas.some((l) => l.sku === anterior)) {
      setLineas((a) => a.filter((l) => l.sku !== anterior));
      agregar(skuSustituto);
    }
  }

  async function cobrar() {
    setError(null);
    try {
      const respuesta = await compra.mutateAsync({
        tienda: tiendaId,
        items: lineas.map((l) => ({ sku: l.sku, cantidad: l.cantidad })),
      });
      setUltimo(respuesta);
      setLineas([]);
    } catch (excepcion) {
      setError(
        excepcion instanceof ErrorApi
          ? excepcion.message
          : "No se pudo cobrar. Intenta de nuevo.",
      );
    }
  }

  const agotado = seleccionado?.stock === 0;

  return (
    <div className="grid gap-3 lg:grid-cols-[320px_minmax(0,1fr)_320px]">
      <div className="h-[calc(100vh-8rem)]">
        <BuscadorProducto
          consulta={consulta}
          onConsulta={setConsulta}
          productos={productos}
          skuSeleccionado={sku}
          onSeleccionar={setSku}
          cargando={isLoading}
        />
      </div>

      <div className="flex flex-col gap-4">
        {!seleccionado && (
          <p className="border border-dashed border-linea px-3 py-6 text-center text-acero">
            Busca un producto para empezar.
          </p>
        )}

        {seleccionado && (
          <>
            <section className="border border-linea bg-white p-3">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <ProductoTile
                  sku={seleccionado.sku}
                  nombre={seleccionado.nombre}
                  categoria={seleccionado.categoria}
                  material={seleccionado.material}
                  uso={seleccionado.uso_recomendado}
                />
                <div className="flex items-center gap-3">
                  <span className="cifra text-lg">{precio(seleccionado.precio)}</span>
                  <span className="cifra text-sm text-acero">
                    {seleccionado.stock} pz
                  </span>
                  <button
                    onClick={() => agregar(seleccionado.sku)}
                    disabled={agotado}
                    className="px-3 py-2 font-medium text-white disabled:opacity-40"
                    style={{ background: "var(--color-acento)" }}
                  >
                    Agregar al ticket
                  </button>
                </div>
              </div>
              <p className="mt-2 text-xs text-acero">
                {seleccionado.descripcion} · uso: {seleccionado.uso_recomendado}
              </p>
              {agotado && (
                <p className="mt-2 border border-red-200 bg-red-50 px-2 py-1 text-xs text-red-700">
                  Agotado. No se puede vender ni recomendar.
                </p>
              )}
            </section>

            <BloqueRecomendacion
              titulo={`Mejor para esta plaza${tienda ? ` · ${tienda.nombre}` : ""}`}
              candidatos={recomendacion?.sustituto ? [recomendacion.sustituto] : []}
              catalogo={catalogo}
              etiquetaAccion="Sustituir"
              onAccion={sustituir}
              vacio="Este producto ya es el adecuado para esta plaza."
            />

            <BloqueRecomendacion
              titulo="Para terminar el trabajo"
              candidatos={recomendacion?.complementos ?? []}
              catalogo={catalogo}
              etiquetaAccion="Agregar"
              onAccion={agregar}
              vacio="Sin complementos disponibles con existencia."
            />
          </>
        )}
      </div>

      <div className="h-[calc(100vh-8rem)]">
        <Ticket
          lineas={lineas}
          onCantidad={cambiarCantidad}
          onQuitar={(s) => cambiarCantidad(s, 0)}
          onCobrar={cobrar}
          cobrando={compra.isPending}
          error={error}
          ultimo={ultimo}
        />
      </div>
    </div>
  );
}
