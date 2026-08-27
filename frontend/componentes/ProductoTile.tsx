"use client";

/**
 * Representacion de un producto sin foto: icono por categoria, chip de color
 * por ambiente y SKU en monoespaciada. Componente de presentacion puro.
 */

import { AMBIENTE, ambienteDe, iconoDe } from "../lib/visual";

type Props = {
  sku: string;
  nombre: string;
  categoria: string;
  material: string;
  uso: string;
  tamano?: "chico" | "normal";
};

export function ProductoTile({
  sku,
  nombre,
  categoria,
  material,
  uso,
  tamano = "normal",
}: Props) {
  const Icono = iconoDe(categoria);
  const ambiente = AMBIENTE[ambienteDe(material, uso)];
  const lado = tamano === "chico" ? 32 : 44;

  return (
    <div className="flex items-center gap-2">
      <div
        className="flex shrink-0 items-center justify-center border"
        style={{
          width: lado,
          height: lado,
          borderColor: ambiente.color,
          // Sobre papel claro un 12% de opacidad basta para leer el ambiente de
          // un vistazo sin que el icono pierda contraste.
          backgroundColor: `${ambiente.color}1F`,
          color: ambiente.color,
        }}
        title={ambiente.etiqueta}
      >
        <Icono size={tamano === "chico" ? 16 : 22} aria-hidden />
      </div>
      <div className="min-w-0">
        <div className="truncate font-medium leading-tight">{nombre}</div>
        <div className="flex items-center gap-2 text-xs text-acero">
          <span className="cifra">{sku}</span>
          <span
            className="truncate"
            style={{ color: ambiente.color }}
            title={material}
          >
            {ambiente.etiqueta}
          </span>
        </div>
      </div>
    </div>
  );
}
