"use client";

/**
 * Tabla de relaciones con sus metricas y sus controles de ajuste.
 * Componente de presentacion puro.
 *
 * Ver sin poder ajustar no cumple el requisito: por eso cada fila trae
 * bloquear, fijar y peso manual, y no solo los numeros.
 */

import { Ban, Pin, RotateCcw } from "lucide-react";
import type { Relacion } from "../lib/api";

type Props = {
  relaciones: Relacion[];
  onEstado: (id: number, estado: string) => void;
  onPeso: (id: number, peso: number | null) => void;
  ajustando: boolean;
};

const ESTADO_ETIQUETA: Record<string, string> = {
  activa: "",
  bloqueada: "bloqueada",
  fijada: "fijada",
};

export function TablaRelaciones({
  relaciones,
  onEstado,
  onPeso,
  ajustando,
}: Props) {
  return (
    <table className="w-full border-collapse text-sm">
      <thead>
        <tr className="border-b border-linea text-left text-xs uppercase tracking-wide text-acero">
          <th className="px-2 py-2 font-medium">Si lleva</th>
          <th className="px-2 py-2 font-medium">Se le ofrece</th>
          <th className="px-2 py-2 font-medium">Tipo</th>
          <th className="px-2 py-2 font-medium">Fuente</th>
          <th className="px-2 py-2 text-right font-medium">Sop.</th>
          <th className="px-2 py-2 text-right font-medium">Conf.</th>
          <th className="px-2 py-2 text-right font-medium">Lift</th>
          <th className="px-2 py-2 text-right font-medium">Score</th>
          <th className="px-2 py-2 text-right font-medium">Peso manual</th>
          <th className="px-2 py-2 text-right font-medium">Ajuste</th>
        </tr>
      </thead>
      <tbody>
        {relaciones.map((r) => {
          const bloqueada = r.estado === "bloqueada";
          const sinExistencia = r.stock_destino === 0 || !r.activo_destino;
          return (
            <tr
              key={r.id}
              className="border-b border-linea"
              style={{ opacity: bloqueada ? 0.45 : 1 }}
            >
              <td className="px-2 py-1.5">
                <span className="cifra text-xs text-acero">{r.sku_origen}</span>{" "}
                <span className="text-xs">{r.nombre_origen}</span>
              </td>
              <td className="px-2 py-1.5">
                <span className="cifra text-xs text-acero">{r.sku_destino}</span>{" "}
                <span className="text-xs">{r.nombre_destino}</span>
                {sinExistencia && (
                  <span
                    className="ml-1 text-[11px] text-red-600"
                    title="Filtrado en el mostrador por no tener existencia"
                  >
                    sin stock
                  </span>
                )}
              </td>
              <td className="px-2 py-1.5 text-xs text-acero">{r.tipo}</td>
              <td className="px-2 py-1.5 text-xs text-acero">{r.fuente}</td>
              <td className="cifra px-2 py-1.5 text-right text-xs">
                {r.soporte ?? "-"}
              </td>
              <td className="cifra px-2 py-1.5 text-right text-xs">
                {r.confianza != null ? r.confianza.toFixed(2) : "-"}
              </td>
              <td className="cifra px-2 py-1.5 text-right text-xs">
                {r.lift != null ? r.lift.toFixed(1) : "-"}
              </td>
              <td className="cifra px-2 py-1.5 text-right text-xs">
                {r.score.toFixed(3)}
              </td>

              <td className="px-2 py-1.5 text-right">
                <input
                  type="number"
                  min={0}
                  step="0.1"
                  defaultValue={r.peso_manual ?? ""}
                  placeholder="auto"
                  aria-label={`Peso manual de ${r.sku_origen} a ${r.sku_destino}`}
                  onBlur={(e) => {
                    const texto = e.target.value.trim();
                    const valor = texto === "" ? null : Number(texto);
                    if (valor !== r.peso_manual) onPeso(r.id, valor);
                  }}
                  className="cifra w-20 border border-linea px-1 py-0.5 text-right text-xs"
                />
              </td>

              <td className="px-2 py-1.5">
                <div className="flex justify-end gap-1">
                  <button
                    onClick={() =>
                      onEstado(r.id, bloqueada ? "activa" : "bloqueada")
                    }
                    disabled={ajustando}
                    title={bloqueada ? "Reactivar relacion" : "Bloquear relacion"}
                    aria-label={
                      bloqueada ? "Reactivar relacion" : "Bloquear relacion"
                    }
                    className="border border-linea p-1 text-acero hover:text-red-600"
                  >
                    {bloqueada ? <RotateCcw size={13} /> : <Ban size={13} />}
                  </button>
                  <button
                    onClick={() =>
                      onEstado(r.id, r.estado === "fijada" ? "activa" : "fijada")
                    }
                    disabled={ajustando}
                    title="Fijar arriba"
                    aria-label="Fijar relacion"
                    className="border border-linea p-1"
                    style={{
                      color:
                        r.estado === "fijada"
                          ? "var(--color-acento)"
                          : "var(--color-acero)",
                    }}
                  >
                    <Pin size={13} />
                  </button>
                  {ESTADO_ETIQUETA[r.estado] && (
                    <span className="self-center text-[11px] text-acero">
                      {ESTADO_ETIQUETA[r.estado]}
                    </span>
                  )}
                </div>
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
