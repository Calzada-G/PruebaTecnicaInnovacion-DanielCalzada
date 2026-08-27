"use client";

/**
 * Representacion de un producto sin foto: icono por categoria, chip de color
 * por ambiente y SKU en monoespaciada. Componente de presentacion puro.
 *
 * El contenedor lleva min-w-0 y el texto recorta: los nombres del catalogo
 * llegan a 44 caracteres y sin esto empujan la columna de al lado o se salen
 * de la tarjeta.
 */

import { AMBIENTE, ambienteDe, iconoDe } from "../lib/visual";

type Props = {
  sku: string;
  nombre: string;
  categoria: string;
  material: string;
  uso: string;
  tamano?: "chico" | "normal";
  /** Deja el nombre en dos lineas en vez de recortarlo a una. */
  nombreCompleto?: boolean;
};

export function ProductoTile({
  sku,
  nombre,
  categoria,
  material,
  uso,
  tamano = "normal",
  nombreCompleto = false,
}: Props) {
  const Icono = iconoDe(categoria);
  const ambiente = AMBIENTE[ambienteDe(material, uso)];
  const lado = tamano === "chico" ? 32 : 44;

  return (
    <div className="flex min-w-0 items-center gap-2">
      <div
        className="flex shrink-0 items-center justify-center rounded-[var(--radio)] border"
        style={{
          width: lado,
          height: lado,
          borderColor: ambiente.color,
          // Sobre papel claro un 12% de opacidad basta para leer el ambiente de
          // un vistazo sin que el icono pierda contraste.
          backgroundColor: `${ambiente.color}1F`,
          color: ambiente.color,
        }}
        title={`${categoria} · ${material}`}
      >
        <Icono size={tamano === "chico" ? 16 : 22} aria-hidden />
      </div>

      <div className="min-w-0 flex-1">
        <div
          className={`${nombreCompleto ? "recorta-2" : "recorta"} font-medium leading-tight`}
          title={nombre}
        >
          {nombre}
        </div>
        <div className="flex min-w-0 items-center gap-1.5 text-xs text-acero">
          <span className="cifra shrink-0">{sku}</span>
          <span
            className="recorta rounded-full px-1.5 text-[11px] leading-4"
            style={{
              background: `${ambiente.color}14`,
              color: ambiente.color,
            }}
            title={material}
          >
            {ambiente.etiqueta}
          </span>
        </div>
      </div>
    </div>
  );
}
