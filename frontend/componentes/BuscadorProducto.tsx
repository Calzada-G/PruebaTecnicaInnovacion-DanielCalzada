"use client";

/**
 * Buscador con navegacion por teclado. Componente de presentacion puro.
 *
 * El vendedor tiene un cliente enfrente: escribe, baja con las flechas y
 * confirma con Enter sin soltar el teclado ni buscar el raton.
 */

import { useEffect, useRef, useState } from "react";
import { Search } from "lucide-react";
import type { Producto } from "../lib/api";
import { precio } from "../lib/visual";
import { ProductoTile } from "./ProductoTile";

type Props = {
  consulta: string;
  onConsulta: (valor: string) => void;
  productos: Producto[];
  skuSeleccionado: string | null;
  onSeleccionar: (sku: string) => void;
  cargando: boolean;
};

export function BuscadorProducto({
  consulta,
  onConsulta,
  productos,
  skuSeleccionado,
  onSeleccionar,
  cargando,
}: Props) {
  const [resaltado, setResaltado] = useState(0);
  const entrada = useRef<HTMLInputElement>(null);

  useEffect(() => setResaltado(0), [consulta]);

  // "/" enfoca el buscador desde cualquier parte, salvo si ya se esta
  // escribiendo en otro campo.
  useEffect(() => {
    function alPulsar(evento: KeyboardEvent) {
      const activo = document.activeElement?.tagName;
      if (evento.key === "/" && activo !== "INPUT" && activo !== "TEXTAREA") {
        evento.preventDefault();
        entrada.current?.focus();
      }
    }
    window.addEventListener("keydown", alPulsar);
    return () => window.removeEventListener("keydown", alPulsar);
  }, []);

  function alTeclear(evento: React.KeyboardEvent) {
    if (evento.key === "ArrowDown") {
      evento.preventDefault();
      setResaltado((i) => Math.min(i + 1, productos.length - 1));
    } else if (evento.key === "ArrowUp") {
      evento.preventDefault();
      setResaltado((i) => Math.max(i - 1, 0));
    } else if (evento.key === "Enter" && productos[resaltado]) {
      evento.preventDefault();
      onSeleccionar(productos[resaltado].sku);
    }
  }

  return (
    <div className="flex h-full flex-col border border-linea bg-white">
      <div className="flex items-center gap-2 border-b border-linea px-2 py-2">
        <Search size={16} className="shrink-0 text-acero" aria-hidden />
        <input
          ref={entrada}
          autoFocus
          value={consulta}
          onChange={(e) => onConsulta(e.target.value)}
          onKeyDown={alTeclear}
          placeholder="Buscar por nombre, material o uso   /"
          aria-label="Buscar producto"
          className="w-full bg-transparent outline-none placeholder:text-acero"
        />
      </div>

      <div className="flex-1 overflow-y-auto">
        {cargando && <p className="p-3 text-acero">Buscando...</p>}

        {!cargando && productos.length === 0 && (
          <p className="p-3 text-acero">
            {consulta
              ? `Sin resultados para "${consulta}".`
              : "Busca un producto para empezar."}
          </p>
        )}

        {productos.map((producto, indice) => {
          const agotado = producto.stock === 0;
          const activo = producto.sku === skuSeleccionado;
          return (
            <button
              key={producto.sku}
              onClick={() => onSeleccionar(producto.sku)}
              onMouseEnter={() => setResaltado(indice)}
              className="block w-full border-b border-linea px-2 py-2 text-left"
              style={{
                background: activo
                  ? "var(--color-papel)"
                  : indice === resaltado
                    ? "#FAFAFB"
                    : "white",
                borderLeft: `3px solid ${activo ? "var(--color-acento)" : "transparent"}`,
                opacity: agotado ? 0.55 : 1,
              }}
            >
              <ProductoTile
                sku={producto.sku}
                nombre={producto.nombre}
                categoria={producto.categoria}
                material={producto.material}
                uso={producto.uso_recomendado}
                tamano="chico"
              />
              <div className="mt-1 flex justify-between text-xs">
                <span className="cifra">{precio(producto.precio)}</span>
                <span className={agotado ? "cifra text-red-600" : "cifra text-acero"}>
                  {agotado ? "agotado" : `${producto.stock} en stock`}
                </span>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
