"use client";

import { Store } from "lucide-react";
import { useTienda } from "../lib/tienda-context";

const PERFIL_LEGIBLE: Record<string, string> = {
  interior_urbano: "interior urbano",
  costero_salino: "costero salino",
  sol_directo_seco: "sol directo y seco",
  taller_metalmecanico: "taller metalmecanico",
};

export function SelectorTienda() {
  const { tiendas, tienda, tiendaId, seleccionar } = useTienda();

  return (
    <div className="flex items-center gap-2">
      <Store size={16} className="text-acero" aria-hidden />
      <select
        value={tiendaId}
        onChange={(e) => seleccionar(e.target.value)}
        aria-label="Tienda"
        className="border border-linea bg-white px-2 py-1 font-medium text-tinta"
        style={{ borderLeft: `3px solid ${tienda?.acento ?? "#6B7280"}` }}
      >
        {tiendas.map((t) => (
          <option key={t.id} value={t.id}>
            {t.nombre}
          </option>
        ))}
      </select>
      {tienda && (
        <span className="text-xs text-acero">
          {PERFIL_LEGIBLE[tienda.perfil] ?? tienda.perfil}
        </span>
      )}
    </div>
  );
}
