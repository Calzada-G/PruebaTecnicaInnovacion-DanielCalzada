"use client";

/** Ticket en curso. Componente de presentacion puro. */

import { Minus, Plus, Trash2 } from "lucide-react";
import type { CompraRespuesta } from "../lib/api";
import { precio } from "../lib/visual";

export type LineaTicket = {
  sku: string;
  nombre: string;
  precio: number;
  cantidad: number;
  stock: number;
};

type Props = {
  lineas: LineaTicket[];
  onCantidad: (sku: string, cantidad: number) => void;
  onQuitar: (sku: string) => void;
  onCobrar: () => void;
  cobrando: boolean;
  error: string | null;
  ultimo: CompraRespuesta | null;
};

export function Ticket({
  lineas,
  onCantidad,
  onQuitar,
  onCobrar,
  cobrando,
  error,
  ultimo,
}: Props) {
  const total = lineas.reduce((suma, l) => suma + l.precio * l.cantidad, 0);

  return (
    <div className="flex h-full flex-col border border-linea bg-white">
      <h2 className="border-b border-linea px-3 py-2 text-xs font-semibold uppercase tracking-wide text-acero">
        Ticket
      </h2>

      <div className="flex-1 overflow-y-auto">
        {lineas.length === 0 && (
          <p className="p-3 text-acero">
            {ultimo
              ? `Cobrado ${ultimo.ticket_id}. Agrega productos para el siguiente.`
              : "Sin productos. Agrega desde la ficha o las recomendaciones."}
          </p>
        )}

        {lineas.map((linea) => (
          <div key={linea.sku} className="border-b border-linea px-3 py-2">
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0">
                <div className="truncate text-sm font-medium">{linea.nombre}</div>
                <div className="cifra text-xs text-acero">{linea.sku}</div>
              </div>
              <button
                onClick={() => onQuitar(linea.sku)}
                aria-label={`Quitar ${linea.sku}`}
                className="shrink-0 text-acero hover:text-red-600"
              >
                <Trash2 size={14} />
              </button>
            </div>

            <div className="mt-1 flex items-center justify-between">
              <div className="flex items-center gap-1">
                <button
                  onClick={() => onCantidad(linea.sku, linea.cantidad - 1)}
                  aria-label="Menos"
                  className="border border-linea px-1"
                >
                  <Minus size={12} />
                </button>
                <span className="cifra w-8 text-center">{linea.cantidad}</span>
                <button
                  onClick={() => onCantidad(linea.sku, linea.cantidad + 1)}
                  disabled={linea.cantidad >= linea.stock}
                  aria-label="Mas"
                  className="border border-linea px-1 disabled:opacity-30"
                >
                  <Plus size={12} />
                </button>
                {linea.cantidad >= linea.stock && (
                  <span className="ml-1 text-[11px] text-acero">
                    tope {linea.stock}
                  </span>
                )}
              </div>
              <span className="cifra text-sm">
                {precio(linea.precio * linea.cantidad)}
              </span>
            </div>
          </div>
        ))}
      </div>

      {error && (
        <p className="border-t border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
          {error}
        </p>
      )}

      <div className="border-t border-linea p-3">
        <div className="mb-2 flex items-baseline justify-between">
          <span className="text-xs uppercase tracking-wide text-acero">Total</span>
          <span className="cifra text-lg font-medium">{precio(total)}</span>
        </div>
        <button
          onClick={onCobrar}
          disabled={lineas.length === 0 || cobrando}
          className="w-full py-2 font-medium text-white disabled:opacity-40"
          style={{ background: "var(--color-acento)" }}
        >
          {cobrando ? "Cobrando..." : "Cobrar"}
        </button>
      </div>
    </div>
  );
}
