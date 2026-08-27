"use client";

import { MapPin } from "lucide-react";
import { useTienda } from "../lib/tienda-context";

/**
 * El perfil en palabras del negocio. 'costero_salino' no le dice nada a nadie
 * fuera del codigo; "cerca del mar" si, y es lo que explica que el sistema
 * proponga inoxidable.
 */
const PERFIL_LEGIBLE: Record<string, string> = {
  interior_urbano: "Interior urbano",
  costero_salino: "Cerca del mar",
  sol_directo_seco: "Sol directo y seco",
  taller_metalmecanico: "Zona de talleres",
};

export function SelectorTienda() {
  const { tiendas, tienda, tiendaId, seleccionar } = useTienda();

  return (
    <div className="flex items-center gap-2">
      <label
        htmlFor="selector-tienda"
        className="hidden text-[11px] uppercase tracking-wide text-acero sm:block"
      >
        Sucursal
      </label>
      <div
        className="flex items-center gap-2 rounded-[var(--radio)] border bg-white pl-2 transition-colors"
        style={{ borderColor: "var(--color-linea)" }}
      >
        <MapPin size={15} style={{ color: "var(--color-acento)" }} aria-hidden />
        <select
          id="selector-tienda"
          value={tiendaId}
          onChange={(e) => seleccionar(e.target.value)}
          className="cursor-pointer bg-transparent py-1.5 pr-2 font-medium text-tinta outline-none"
        >
          {tiendas.map((t) => (
            <option key={t.id} value={t.id}>
              {t.nombre}
            </option>
          ))}
        </select>
      </div>
      {tienda && (
        <span
          className="hidden shrink-0 rounded-full px-2 py-0.5 text-[11px] font-medium lg:inline"
          style={{
            background: "color-mix(in srgb, var(--color-acento) 12%, #fff)",
            color: "var(--color-acento)",
          }}
        >
          {PERFIL_LEGIBLE[tienda.perfil] ?? tienda.perfil}
        </span>
      )}
    </div>
  );
}
