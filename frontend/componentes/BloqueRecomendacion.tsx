"use client";

/**
 * Bloque de recomendaciones. Componente de presentacion puro.
 *
 * Cada tarjeta muestra SIEMPRE de donde sale la sugerencia y por que.
 * El vendedor tiene que poder repetirle el motivo al cliente, y el
 * negocio tiene que poder auditar de donde salio.
 */

import { Plus, Repeat } from "lucide-react";
import type { Candidato, Producto } from "../lib/api";
import { etiquetaFuente, precio } from "../lib/visual";
import { ProductoTile } from "./ProductoTile";

type Props = {
  titulo: string;
  descripcion: string;
  candidatos: Candidato[];
  catalogo: Map<string, Producto>;
  etiquetaAccion: string;
  onAccion: (sku: string) => void;
  vacio: string;
  destacado?: boolean;
};

export function BloqueRecomendacion({
  titulo,
  descripcion,
  candidatos,
  catalogo,
  etiquetaAccion,
  onAccion,
  vacio,
  destacado = false,
}: Props) {
  const Icono = destacado ? Repeat : Plus;

  return (
    <section>
      <div className="mb-2 flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
        <h2 className="text-sm font-semibold">{titulo}</h2>
        <p className="text-xs text-acero">{descripcion}</p>
      </div>

      {candidatos.length === 0 ? (
        <p className="rounded-[var(--radio)] border border-dashed border-linea px-3 py-3 text-xs text-acero">
          {vacio}
        </p>
      ) : (
        <ul className="grid gap-2 sm:grid-cols-2 2xl:grid-cols-3">
          {candidatos.map((candidato) => {
            const producto = catalogo.get(candidato.sku);
            if (!producto) return null;
            const pocas = producto.stock <= 5;

            return (
              <li
                key={candidato.sku}
                className="tarjeta tarjeta-activa aparece flex flex-col gap-2 p-2.5"
                style={
                  destacado
                    ? { borderColor: "var(--color-acento)", borderWidth: 2 }
                    : undefined
                }
              >
                <div className="flex min-w-0 items-start justify-between gap-2">
                  <ProductoTile
                    sku={producto.sku}
                    nombre={producto.nombre}
                    categoria={producto.categoria}
                    material={producto.material}
                    uso={producto.uso_recomendado}
                    tamano="chico"
                    nombreCompleto
                  />
                  <span
                    className="shrink-0 rounded-full border px-1.5 py-0.5 text-[10px] font-medium leading-4 text-acero"
                    style={{ borderColor: "var(--color-linea)" }}
                    title={
                      candidato.soporte
                        ? `Evidencia de ventas — soporte ${candidato.soporte}, confianza ${candidato.confianza}, lift ${candidato.lift}`
                        : "Derivado del tipo de producto y del perfil de la plaza"
                    }
                  >
                    {etiquetaFuente(candidato.fuente, candidato.soporte)}
                  </span>
                </div>

                {/* Altura fija de dos lineas: las justificaciones van de 30 a
                    123 caracteres y sin esto las tarjetas quedan desparejas. */}
                <p className="recorta-2 min-h-[2.1rem] text-xs leading-snug text-acero">
                  {candidato.justificacion}
                </p>

                <div className="mt-auto flex items-center justify-between gap-2 border-t border-linea pt-2">
                  <span className="min-w-0 text-xs">
                    <span className="cifra font-medium">
                      {precio(producto.precio)}
                    </span>
                    <span
                      className="cifra ml-2"
                      style={{ color: pocas ? "var(--color-alerta)" : "var(--color-acero)" }}
                    >
                      {producto.stock} pz
                    </span>
                  </span>
                  <button
                    onClick={() => onAccion(candidato.sku)}
                    className="boton boton-primario flex shrink-0 items-center gap-1 px-2.5 py-1 text-xs"
                  >
                    <Icono size={13} aria-hidden />
                    {etiquetaAccion}
                  </button>
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
