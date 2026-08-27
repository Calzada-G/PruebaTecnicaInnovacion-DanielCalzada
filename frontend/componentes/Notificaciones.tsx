"use client";

/** Pila de avisos, abajo a la derecha. Componente de presentacion puro. */

import { AlertCircle, CheckCircle2, Info, X } from "lucide-react";
import { useAvisos, type TipoAviso } from "../lib/notificaciones";

const ESTILO: Record<
  TipoAviso,
  { icono: typeof Info; color: string; fondo: string }
> = {
  exito: { icono: CheckCircle2, color: "#15803d", fondo: "#f0fdf4" },
  error: { icono: AlertCircle, color: "#b91c1c", fondo: "#fef2f2" },
  info: { icono: Info, color: "#1d4ed8", fondo: "#eff6ff" },
};

export function Notificaciones() {
  const { avisos, cerrar } = useAvisos();

  return (
    <div
      // aria-live para que un lector de pantalla anuncie el aviso sin robar el
      // foco: el vendedor sigue escribiendo mientras el aviso aparece.
      aria-live="polite"
      aria-atomic="false"
      className="pointer-events-none fixed bottom-4 right-4 z-50 flex w-[min(22rem,calc(100vw-2rem))] flex-col gap-2"
    >
      {avisos.map((aviso) => {
        const estilo = ESTILO[aviso.tipo];
        const Icono = estilo.icono;
        return (
          <div
            key={aviso.id}
            role={aviso.tipo === "error" ? "alert" : "status"}
            className={`pointer-events-auto flex items-start gap-2 rounded-[var(--radio)] border p-3 shadow-lg ${
              aviso.saliendo ? "aviso-sale" : "aviso-entra"
            }`}
            style={{
              background: estilo.fondo,
              borderColor: `color-mix(in srgb, ${estilo.color} 30%, transparent)`,
            }}
          >
            <Icono size={16} style={{ color: estilo.color }} className="mt-0.5 shrink-0" />
            <div className="min-w-0 flex-1">
              <p
                className="text-sm font-medium leading-snug"
                style={{ color: estilo.color }}
              >
                {aviso.titulo}
              </p>
              {aviso.detalle && (
                <p className="recorta-3 mt-0.5 text-xs leading-snug text-acero">
                  {aviso.detalle}
                </p>
              )}
            </div>
            <button
              onClick={() => cerrar(aviso.id)}
              aria-label="Cerrar aviso"
              className="boton shrink-0 p-0.5 text-acero hover:text-tinta"
            >
              <X size={14} />
            </button>
          </div>
        );
      })}
    </div>
  );
}
