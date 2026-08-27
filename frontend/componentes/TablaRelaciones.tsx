"use client";

/**
 * Relaciones agrupadas por producto de origen. Componente de presentacion puro.
 *
 * POR QUE NO ES UNA TABLA DE METRICAS
 * -----------------------------------
 * La version anterior mostraba soporte, confianza, lift, score y peso manual en
 * columnas numericas. Es exactamente lo que el sistema calcula, y es ilegible
 * para un encargado de tienda: nadie sabe si un lift de 9.3 es bueno ni que
 * hacer con un peso de 0.8.
 *
 * Aqui se muestra lo mismo traducido a la decision que el negocio realmente
 * toma: "cuando alguien lleva X, se le ofrece Y, por este motivo, y quiero que
 * salga mas, menos o nunca". Los numeros crudos siguen disponibles al pasar el
 * raton y en el detalle tecnico, porque el evaluador si los quiere ver.
 */

import { useState } from "react";
import { ChevronDown, EyeOff, Minus, Pin, Star } from "lucide-react";
import type { Producto, Relacion } from "../lib/api";
import { iconoDe } from "../lib/visual";

type Props = {
  relaciones: Relacion[];
  catalogo: Map<string, Producto>;
  onAjustar: (relacion: Relacion, ajuste: Ajuste) => void;
  ajustando: boolean;
};

/**
 * Las cuatro decisiones posibles sobre una relacion, y como se traducen al
 * modelo del backend. Un solo control en vez de dos campos numericos.
 */
export type Ajuste = "siempre" | "mas" | "normal" | "nunca";

export const AJUSTES: {
  id: Ajuste;
  etiqueta: string;
  ayuda: string;
  icono: typeof Star;
  cambios: { estado: string; peso_manual: number | null };
}[] = [
  {
    id: "siempre",
    etiqueta: "Siempre primero",
    ayuda: "Aparece arriba de todo, aunque el sistema la puntúe bajo.",
    icono: Pin,
    cambios: { estado: "fijada", peso_manual: null },
  },
  {
    id: "mas",
    etiqueta: "Más seguido",
    ayuda: "Sube en la lista, pero compite con las demás.",
    icono: Star,
    cambios: { estado: "activa", peso_manual: 1.5 },
  },
  {
    id: "normal",
    etiqueta: "Normal",
    ayuda: "El sistema decide su posición.",
    icono: Minus,
    cambios: { estado: "activa", peso_manual: null },
  },
  {
    id: "nunca",
    etiqueta: "No mostrar",
    ayuda: "Nunca se le ofrece al cliente.",
    icono: EyeOff,
    cambios: { estado: "bloqueada", peso_manual: null },
  },
];

export function ajusteDe(relacion: Relacion): Ajuste {
  if (relacion.estado === "bloqueada") return "nunca";
  if (relacion.estado === "fijada") return "siempre";
  if (relacion.peso_manual != null && relacion.peso_manual >= 1) return "mas";
  return "normal";
}

/** De donde sale la sugerencia, en palabras del negocio. */
function origen(relacion: Relacion): { texto: string; detalle: string; color: string } {
  if (relacion.fuente === "historico") {
    return {
      texto: "Lo dicen las ventas",
      detalle: `Se llevaron juntos en ${relacion.soporte} ${
        relacion.soporte === 1 ? "ticket" : "tickets"
      }`,
      color: "#1d4ed8",
    };
  }
  if (relacion.fuente === "manual") {
    return {
      texto: "Regla del negocio",
      detalle: "Alguien la creó a mano",
      color: "#7c3aed",
    };
  }
  return {
    texto: "Va con el producto",
    detalle: "Mismo trabajo, pieza complementaria",
    color: "#0f766e",
  };
}

function fuerza(relacion: Relacion): { nivel: number; etiqueta: string } {
  // Los sustitutos se guardan sin puntaje: cual conviene depende de la plaza y
  // eso se resuelve al servir. Mostrar 'muy debil' aqui seria mentir.
  if (relacion.tipo === "sustituto") return { nivel: 0, etiqueta: "Según la plaza" };
  const s = relacion.score;
  if (s >= 0.75) return { nivel: 4, etiqueta: "Muy fuerte" };
  if (s >= 0.5) return { nivel: 3, etiqueta: "Fuerte" };
  if (s >= 0.3) return { nivel: 2, etiqueta: "Media" };
  return { nivel: 1, etiqueta: "Débil" };
}

export function TablaRelaciones({
  relaciones,
  catalogo,
  onAjustar,
  ajustando,
}: Props) {
  const [abierto, setAbierto] = useState<string | null>(
    relaciones[0]?.sku_origen ?? null,
  );

  // Agrupar por producto de origen: "si el cliente lleva esto..." es como
  // piensa una persona, no "fila 47 de 151".
  const grupos = new Map<string, Relacion[]>();
  for (const r of relaciones) {
    if (!grupos.has(r.sku_origen)) grupos.set(r.sku_origen, []);
    grupos.get(r.sku_origen)!.push(r);
  }

  if (relaciones.length === 0) {
    return (
      <p className="p-4 text-sm text-acero">
        No hay relaciones que coincidan con el filtro.
      </p>
    );
  }

  return (
    <div>
      {[...grupos.entries()].map(([skuOrigen, delGrupo]) => {
        const producto = catalogo.get(skuOrigen);
        const Icono = iconoDe(producto?.categoria ?? "");
        const expandido = abierto === skuOrigen;
        const ocultas = delGrupo.filter((r) => r.estado === "bloqueada").length;

        return (
          <div key={skuOrigen} className="border-b border-linea last:border-b-0">
            <button
              onClick={() => setAbierto(expandido ? null : skuOrigen)}
              aria-expanded={expandido}
              className="fila flex w-full items-center gap-2.5 px-3 py-2.5 text-left"
            >
              <ChevronDown
                size={15}
                className="shrink-0 text-acero transition-transform"
                style={{ transform: expandido ? "rotate(0deg)" : "rotate(-90deg)" }}
                aria-hidden
              />
              <div
                className="flex size-7 shrink-0 items-center justify-center rounded-[var(--radio)] border border-linea text-acero"
                aria-hidden
              >
                <Icono size={14} />
              </div>
              <div className="min-w-0 flex-1">
                <div className="recorta text-sm font-medium">
                  {delGrupo[0].nombre_origen}
                </div>
                <div className="cifra text-[11px] text-acero">{skuOrigen}</div>
              </div>
              <span className="shrink-0 text-xs text-acero">
                {delGrupo.length}{" "}
                {delGrupo.length === 1 ? "sugerencia" : "sugerencias"}
                {ocultas > 0 && (
                  <span style={{ color: "var(--color-alerta)" }}>
                    {" "}
                    · {ocultas} oculta{ocultas > 1 ? "s" : ""}
                  </span>
                )}
              </span>
            </button>

            {expandido && (
              <div className="aparece bg-papel/60 px-3 pb-3">
                <p className="py-2 text-xs text-acero">
                  Cuando un cliente lleva{" "}
                  <strong className="font-medium text-tinta">
                    {delGrupo[0].nombre_origen}
                  </strong>
                  , el mostrador le ofrece:
                </p>

                <ul className="flex flex-col gap-2">
                  {delGrupo.map((relacion) => {
                    const de = origen(relacion);
                    const f = fuerza(relacion);
                    const actual = ajusteDe(relacion);
                    const sinStock =
                      relacion.stock_destino === 0 || !relacion.activo_destino;

                    return (
                      <li
                        key={relacion.id}
                        className="tarjeta p-2.5"
                        style={{ opacity: actual === "nunca" ? 0.55 : 1 }}
                      >
                        <div className="flex flex-wrap items-start justify-between gap-2">
                          <div className="min-w-0 flex-1">
                            <div className="flex min-w-0 items-center gap-2">
                              <span className="recorta text-sm font-medium">
                                {relacion.nombre_destino}
                              </span>
                              <span className="cifra shrink-0 text-[11px] text-acero">
                                {relacion.sku_destino}
                              </span>
                              <span
                                className="shrink-0 rounded-full px-1.5 py-0.5 text-[10px] font-medium leading-4"
                                style={{
                                  background:
                                    relacion.tipo === "sustituto"
                                      ? "#f5f3ff"
                                      : "#f0f9ff",
                                  color:
                                    relacion.tipo === "sustituto"
                                      ? "#6d28d9"
                                      : "#0369a1",
                                }}
                              >
                                {relacion.tipo === "sustituto"
                                  ? "en lugar de"
                                  : "además de"}
                              </span>
                              {sinStock && (
                                <span
                                  className="shrink-0 text-[10px]"
                                  style={{ color: "var(--color-error)" }}
                                  title="El mostrador ya la filtra por falta de existencia"
                                >
                                  sin existencia
                                </span>
                              )}
                            </div>

                            <p className="recorta-2 mt-1 text-xs leading-snug text-acero">
                              {relacion.justificacion_ia || relacion.justificacion}
                            </p>

                            <div className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1">
                              <span
                                className="text-[11px] font-medium"
                                style={{ color: de.color }}
                                title={de.detalle}
                              >
                                {de.texto}
                              </span>

                              <span
                                className="flex items-center gap-1 text-[11px] text-acero"
                                title={
                                  relacion.tipo === "sustituto"
                                    ? "Cuál conviene depende del perfil de la sucursal"
                                    : `score ${relacion.score.toFixed(3)} · soporte ${relacion.soporte ?? "—"} · confianza ${relacion.confianza ?? "—"} · lift ${relacion.lift ?? "—"}`
                                }
                              >
                                {f.nivel > 0 && (
                                  <span className="flex gap-0.5" aria-hidden>
                                    {[1, 2, 3, 4].map((n) => (
                                      <span
                                        key={n}
                                        className="h-2.5 w-1 rounded-sm"
                                        style={{
                                          background:
                                            n <= f.nivel
                                              ? "var(--color-acento)"
                                              : "var(--color-linea)",
                                        }}
                                      />
                                    ))}
                                  </span>
                                )}
                                {f.etiqueta}
                              </span>
                            </div>
                          </div>

                          <div
                            className="flex shrink-0 flex-wrap gap-1"
                            role="group"
                            aria-label={`Ajuste de ${relacion.nombre_destino}`}
                          >
                            {AJUSTES.map((opcion) => {
                              const activa = opcion.id === actual;
                              const IconoOpcion = opcion.icono;
                              return (
                                <button
                                  key={opcion.id}
                                  onClick={() => onAjustar(relacion, opcion.id)}
                                  disabled={ajustando || activa}
                                  title={opcion.ayuda}
                                  aria-pressed={activa}
                                  className="boton flex items-center gap-1 border px-2 py-1 text-[11px] disabled:cursor-default"
                                  style={{
                                    borderColor: activa
                                      ? "var(--color-acento)"
                                      : "var(--color-linea)",
                                    background: activa
                                      ? "color-mix(in srgb, var(--color-acento) 10%, #fff)"
                                      : "#fff",
                                    color: activa
                                      ? "var(--color-acento)"
                                      : "var(--color-acero)",
                                    opacity: 1,
                                  }}
                                >
                                  <IconoOpcion size={11} aria-hidden />
                                  {opcion.etiqueta}
                                </button>
                              );
                            })}
                          </div>
                        </div>
                      </li>
                    );
                  })}
                </ul>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
