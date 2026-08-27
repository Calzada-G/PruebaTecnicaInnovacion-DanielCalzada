"use client";

/** Ticket en curso. Componente de presentacion puro. */

import { useEffect } from "react";
import { Check, Minus, Plus, Receipt, Trash2 } from "lucide-react";
import type { CompraRespuesta } from "../lib/api";
import type { LineaTicket } from "../lib/ticket-context";
import { precio } from "../lib/visual";

type Props = {
  lineas: LineaTicket[];
  onCantidad: (sku: string, cantidad: number) => void;
  onQuitar: (sku: string) => void;
  onCobrar: () => void;
  cobrando: boolean;
  error: string | null;
  ultimo: CompraRespuesta | null;
  nombreTienda: string;
};

export function Ticket({
  lineas,
  onCantidad,
  onQuitar,
  onCobrar,
  cobrando,
  error,
  ultimo,
  nombreTienda,
}: Props) {
  const total = lineas.reduce((suma, l) => suma + l.precio * l.cantidad, 0);
  const piezas = lineas.reduce((suma, l) => suma + l.cantidad, 0);

  // Ctrl+Enter cobra desde cualquier parte: el vendedor viene de escribir en el
  // buscador y no deberia soltar el teclado para cerrar la venta.
  useEffect(() => {
    function alPulsar(evento: KeyboardEvent) {
      if (evento.key === "Enter" && evento.ctrlKey && lineas.length && !cobrando) {
        evento.preventDefault();
        onCobrar();
      }
    }
    window.addEventListener("keydown", alPulsar);
    return () => window.removeEventListener("keydown", alPulsar);
  }, [lineas.length, cobrando, onCobrar]);

  return (
    <div className="tarjeta flex h-full flex-col overflow-hidden">
      <div className="flex items-center justify-between gap-2 border-b border-linea px-3 py-2">
        <h2 className="flex items-center gap-1.5 text-sm font-semibold">
          <Receipt size={15} style={{ color: "var(--color-acento)" }} aria-hidden />
          Ticket
        </h2>
        <span className="cifra recorta text-[11px] text-acero">{nombreTienda}</span>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto">
        {lineas.length === 0 && (
          <div className="p-3">
            {ultimo ? (
              <div
                className="aparece rounded-[var(--radio)] border p-2.5"
                style={{ borderColor: "#bbf7d0", background: "#f0fdf4" }}
              >
                <p
                  className="flex items-center gap-1.5 text-sm font-medium"
                  style={{ color: "var(--color-exito)" }}
                >
                  <Check size={15} aria-hidden /> Cobrado {ultimo.ticket_id}
                </p>
                <p className="cifra mt-1 text-lg font-medium">
                  {precio(ultimo.total)}
                </p>
                <p className="mt-1 text-xs text-acero">
                  Inventario descontado. Listo para el siguiente cliente.
                </p>
              </div>
            ) : (
              <>
                <p className="text-sm font-medium">Ticket vacío</p>
                <p className="mt-1 text-xs text-acero">
                  Agrega productos desde la ficha o desde las sugerencias.
                </p>
              </>
            )}
          </div>
        )}

        {lineas.map((linea) => {
          const tope = linea.cantidad >= linea.stock;
          return (
            <div key={linea.sku} className="fila border-b border-linea px-3 py-2">
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <div className="recorta-2 text-sm font-medium leading-tight" title={linea.nombre}>
                    {linea.nombre}
                  </div>
                  <div className="cifra text-[11px] text-acero">{linea.sku}</div>
                </div>
                <button
                  onClick={() => onQuitar(linea.sku)}
                  aria-label={`Quitar ${linea.nombre}`}
                  title="Quitar del ticket"
                  className="boton shrink-0 rounded p-1 text-acero hover:bg-red-50 hover:text-red-600"
                >
                  <Trash2 size={14} />
                </button>
              </div>

              <div className="mt-1.5 flex items-center justify-between gap-2">
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => onCantidad(linea.sku, linea.cantidad - 1)}
                    aria-label={`Quitar una unidad de ${linea.nombre}`}
                    className="boton boton-suave px-1.5 py-0.5"
                  >
                    <Minus size={12} />
                  </button>
                  <span className="cifra w-8 text-center font-medium">
                    {linea.cantidad}
                  </span>
                  <button
                    onClick={() => onCantidad(linea.sku, linea.cantidad + 1)}
                    disabled={tope}
                    aria-label={`Agregar una unidad de ${linea.nombre}`}
                    className="boton boton-suave px-1.5 py-0.5"
                  >
                    <Plus size={12} />
                  </button>
                  {tope && (
                    <span
                      className="ml-1 text-[10px]"
                      style={{ color: "var(--color-alerta)" }}
                      title="No hay más existencia de este producto"
                    >
                      todo el stock
                    </span>
                  )}
                </div>
                <span className="cifra shrink-0 text-sm font-medium">
                  {precio(linea.precio * linea.cantidad)}
                </span>
              </div>
            </div>
          );
        })}
      </div>

      {error && (
        <p
          role="alert"
          className="aparece border-t px-3 py-2 text-xs"
          style={{
            borderColor: "#fecaca",
            background: "#fef2f2",
            color: "var(--color-error)",
          }}
        >
          {error}
        </p>
      )}

      <div className="border-t border-linea p-3">
        <div className="mb-2 flex items-baseline justify-between gap-2">
          <span className="text-[11px] uppercase tracking-wide text-acero">
            {piezas > 0 ? `${piezas} ${piezas === 1 ? "pieza" : "piezas"}` : "Total"}
          </span>
          <span className="cifra text-xl font-medium">{precio(total)}</span>
        </div>
        <button
          onClick={onCobrar}
          disabled={lineas.length === 0 || cobrando}
          className="boton boton-primario w-full py-2.5"
        >
          {cobrando ? "Cobrando…" : "Cobrar"}
        </button>
        {lineas.length > 0 && (
          <p className="mt-1 text-center text-[10px] text-acero">
            <span className="cifra">Ctrl+Enter</span> para cobrar
          </p>
        )}
      </div>
    </div>
  );
}
