"use client";

/**
 * Bloque de recomendaciones. Componente de presentacion puro.
 *
 * Cada tarjeta muestra SIEMPRE su procedencia ("2 tickets" / "por atributos" /
 * "manual") y su justificacion. No es adorno: el vendedor tiene que poder
 * repetirle al cliente por que le esta ofreciendo eso, y el negocio tiene que
 * poder auditar de donde salio la sugerencia.
 */

import type { Candidato, Producto } from "../lib/api";
import { etiquetaFuente, precio } from "../lib/visual";
import { ProductoTile } from "./ProductoTile";

type Props = {
  titulo: string;
  candidatos: Candidato[];
  catalogo: Map<string, Producto>;
  etiquetaAccion: string;
  onAccion: (sku: string) => void;
  vacio: string;
};

export function BloqueRecomendacion({
  titulo,
  candidatos,
  catalogo,
  etiquetaAccion,
  onAccion,
  vacio,
}: Props) {
  return (
    <section>
      <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-acero">
        {titulo}
      </h2>

      {candidatos.length === 0 ? (
        <p className="border border-dashed border-linea px-3 py-2 text-acero">
          {vacio}
        </p>
      ) : (
        <ul className="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
          {candidatos.map((candidato) => {
            const producto = catalogo.get(candidato.sku);
            if (!producto) return null;
            return (
              <li
                key={candidato.sku}
                className="flex flex-col gap-2 border border-linea bg-white p-2"
              >
                <div className="flex items-start justify-between gap-2">
                  <ProductoTile
                    sku={producto.sku}
                    nombre={producto.nombre}
                    categoria={producto.categoria}
                    material={producto.material}
                    uso={producto.uso_recomendado}
                    tamano="chico"
                  />
                  <span
                    className="cifra shrink-0 border px-1 text-[11px] leading-5"
                    style={{
                      borderColor: "var(--color-linea)",
                      color: "var(--color-acero)",
                    }}
                    title={
                      candidato.lift
                        ? `soporte ${candidato.soporte}, confianza ${candidato.confianza}, lift ${candidato.lift}`
                        : "derivado de los atributos del producto"
                    }
                  >
                    {etiquetaFuente(candidato.fuente, candidato.soporte)}
                  </span>
                </div>

                <p className="text-xs leading-snug text-acero">
                  {candidato.justificacion}
                </p>

                <div className="mt-auto flex items-center justify-between gap-2">
                  <span className="cifra text-xs">
                    {precio(producto.precio)}
                    <span className="ml-2 text-acero">{producto.stock} pz</span>
                  </span>
                  <button
                    onClick={() => onAccion(candidato.sku)}
                    className="border px-2 py-1 text-xs font-medium text-white"
                    style={{
                      background: "var(--color-acento)",
                      borderColor: "var(--color-acento)",
                    }}
                  >
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
