"use client";

/**
 * Buscador con navegacion por teclado. Componente de presentacion puro.
 *
 * El vendedor tiene un cliente enfrente: escribe, baja con las flechas y
 * confirma con Enter sin soltar el teclado ni buscar el raton.
 */

import { useEffect, useRef, useState } from "react";
import { Search, X } from "lucide-react";
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

const SUGERENCIAS = ["soplete", "tornillo", "tubo", "cable", "candado"];

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
  const lista = useRef<HTMLDivElement>(null);

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

  // Con 28 productos la lista se sale de la caja: si el resaltado baja fuera
  // de la vista, el teclado dejaria de servir sin scroll manual.
  useEffect(() => {
    lista.current
      ?.querySelectorAll("button")
      [resaltado]?.scrollIntoView({ block: "nearest" });
  }, [resaltado]);

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
    } else if (evento.key === "Escape") {
      onConsulta("");
    }
  }

  return (
    <div className="tarjeta flex h-full flex-col overflow-hidden">
      <div className="flex items-center gap-2 border-b border-linea px-2.5 py-2">
        <Search size={16} className="shrink-0 text-acero" aria-hidden />
        <input
          ref={entrada}
          autoFocus
          value={consulta}
          onChange={(e) => onConsulta(e.target.value)}
          onKeyDown={alTeclear}
          placeholder="Buscar producto…"
          aria-label="Buscar producto"
          className="w-full min-w-0 bg-transparent outline-none placeholder:text-acero"
        />
        {consulta ? (
          <button
            onClick={() => onConsulta("")}
            aria-label="Limpiar búsqueda"
            className="boton shrink-0 text-acero hover:text-tinta"
          >
            <X size={14} />
          </button>
        ) : (
          <kbd className="cifra shrink-0 rounded border border-linea px-1 text-[10px] text-acero">
            /
          </kbd>
        )}
      </div>

      <div ref={lista} className="min-h-0 flex-1 overflow-y-auto">
        {cargando && <p className="p-3 text-xs text-acero">Buscando…</p>}

        {!cargando && productos.length === 0 && (
          <div className="p-3">
            <p className="text-sm font-medium">
              {consulta ? "Sin resultados" : "Busca un producto para empezar."}
            </p>
            <p className="mt-1 text-xs text-acero">
              {consulta
                ? `Nada coincide con "${consulta}". Puedes buscar por nombre, material o uso.`
                : "También encuentra por material o por uso: prueba con «salino» o «interior»."}
            </p>
            <div className="mt-2 flex flex-wrap gap-1">
              {SUGERENCIAS.map((s) => (
                <button
                  key={s}
                  onClick={() => onConsulta(s)}
                  className="boton boton-suave px-2 py-0.5 text-xs"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {productos.map((producto, indice) => {
          const agotado = producto.stock === 0;
          const pocas = producto.stock > 0 && producto.stock <= 5;
          const activo = producto.sku === skuSeleccionado;
          return (
            <button
              key={producto.sku}
              onClick={() => onSeleccionar(producto.sku)}
              onMouseEnter={() => setResaltado(indice)}
              className="fila block w-full border-b border-linea px-2.5 py-2 text-left"
              style={{
                background: activo
                  ? "color-mix(in srgb, var(--color-acento) 8%, #fff)"
                  : indice === resaltado
                    ? "#fafafb"
                    : "#fff",
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
              <div className="mt-1 flex items-center justify-between gap-2 text-xs">
                <span className="cifra font-medium">{precio(producto.precio)}</span>
                <span
                  className="cifra shrink-0"
                  style={{
                    color: agotado
                      ? "var(--color-error)"
                      : pocas
                        ? "var(--color-alerta)"
                        : "var(--color-acero)",
                  }}
                >
                  {agotado ? "agotado" : `${producto.stock} pz`}
                </span>
              </div>
            </button>
          );
        })}
      </div>

      {productos.length > 0 && (
        <div className="border-t border-linea px-2.5 py-1.5 text-[11px] text-acero">
          <span className="cifra">↑↓</span> moverse ·{" "}
          <span className="cifra">Enter</span> elegir
        </div>
      )}
    </div>
  );
}
