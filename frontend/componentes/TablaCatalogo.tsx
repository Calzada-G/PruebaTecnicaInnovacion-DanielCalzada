"use client";

/**
 * Tabla de catalogo con edicion en linea. Componente de presentacion puro.
 *
 * Se edita sobre la propia fila y no en un modal: el encargado corrige precios
 * y existencias de varios productos seguidos, y abrir y cerrar un dialogo por
 * cada uno multiplica los clics sin aportar nada.
 */

import { useState } from "react";
import { Check, Pencil, Trash2, Undo2, X } from "lucide-react";
import type { Producto } from "../lib/api";
import { precio } from "../lib/visual";
import { ProductoTile } from "./ProductoTile";

type Props = {
  productos: Producto[];
  onGuardar: (sku: string, cambios: Partial<Producto>) => void;
  onEliminar: (producto: Producto) => void;
  onReactivar: (producto: Producto) => void;
  guardando: boolean;
};

export function TablaCatalogo({
  productos,
  onGuardar,
  onEliminar,
  onReactivar,
  guardando,
}: Props) {
  const [editando, setEditando] = useState<string | null>(null);
  const [borrador, setBorrador] = useState({ precio: "", stock: "" });

  function abrir(producto: Producto) {
    setEditando(producto.sku);
    setBorrador({ precio: String(producto.precio), stock: String(producto.stock) });
  }

  function guardar(sku: string) {
    const cambios: Partial<Producto> = {};
    const p = Number(borrador.precio);
    const s = Number(borrador.stock);
    if (Number.isFinite(p) && p >= 0) cambios.precio = p;
    if (Number.isInteger(s) && s >= 0) cambios.stock = s;
    onGuardar(sku, cambios);
    setEditando(null);
  }

  function alTeclear(evento: React.KeyboardEvent, sku: string) {
    if (evento.key === "Enter") guardar(sku);
    if (evento.key === "Escape") setEditando(null);
  }

  // table-fixed con anchos declarados: sin esto el navegador reparte a ojo y le
  // da a "para que sirve" el espacio que necesita el nombre, que es la columna
  // por la que el encargado localiza lo que viene a corregir.
  return (
    <table className="w-full table-fixed border-collapse">
      <thead>
        <tr className="cabecera text-left text-[11px] uppercase">
          <th className="w-[44%] px-3 py-2 font-medium">Producto</th>
          <th className="hidden w-[26%] px-3 py-2 font-medium lg:table-cell">
            Para qué sirve
          </th>
          <th className="w-28 px-3 py-2 text-right font-medium">Precio</th>
          <th className="w-24 px-3 py-2 text-right font-medium">Existencia</th>
          <th className="w-24 px-3 py-2 text-right font-medium">Acciones</th>
        </tr>
      </thead>
      <tbody>
        {productos.map((producto) => {
          const enEdicion = editando === producto.sku;
          const agotado = producto.stock === 0;
          const pocas = producto.stock > 0 && producto.stock <= 5;

          return (
            <tr
              key={producto.sku}
              className="fila border-b border-linea last:border-b-0"
              style={{ opacity: producto.activo ? 1 : 0.55 }}
            >
              <td className="px-3 py-2">
                <ProductoTile
                  sku={producto.sku}
                  nombre={producto.nombre}
                  categoria={producto.categoria}
                  material={producto.material}
                  uso={producto.uso_recomendado}
                  tamano="chico"
                  nombreCompleto
                />
                {!producto.activo && (
                  <span
                    className="mt-1 inline-block rounded-full px-1.5 py-0.5 text-[10px] font-medium"
                    style={{ background: "#fef2f2", color: "var(--color-error)" }}
                  >
                    dado de baja
                  </span>
                )}
              </td>

              <td className="hidden px-3 py-2 align-top lg:table-cell">
                <span
                  className="recorta-2 text-xs leading-snug text-acero"
                  title={producto.uso_recomendado}
                >
                  {producto.uso_recomendado}
                </span>
              </td>

              <td className="px-3 py-2 text-right align-top">
                {enEdicion ? (
                  <input
                    type="number"
                    min={0}
                    step="0.01"
                    autoFocus
                    value={borrador.precio}
                    onChange={(e) =>
                      setBorrador((b) => ({ ...b, precio: e.target.value }))
                    }
                    onKeyDown={(e) => alTeclear(e, producto.sku)}
                    aria-label={`Precio de ${producto.nombre}`}
                    className="cifra w-24 rounded border border-linea px-1.5 py-1 text-right outline-none"
                  />
                ) : (
                  <span className="cifra">{precio(producto.precio)}</span>
                )}
              </td>

              <td className="px-3 py-2 text-right align-top">
                {enEdicion ? (
                  <input
                    type="number"
                    min={0}
                    step="1"
                    value={borrador.stock}
                    onChange={(e) =>
                      setBorrador((b) => ({ ...b, stock: e.target.value }))
                    }
                    onKeyDown={(e) => alTeclear(e, producto.sku)}
                    aria-label={`Existencia de ${producto.nombre}`}
                    className="cifra w-20 rounded border border-linea px-1.5 py-1 text-right outline-none"
                  />
                ) : (
                  <span
                    className="cifra"
                    style={{
                      color: agotado
                        ? "var(--color-error)"
                        : pocas
                          ? "var(--color-alerta)"
                          : "var(--color-tinta)",
                    }}
                    title={
                      agotado
                        ? "No se puede vender ni recomendar"
                        : pocas
                          ? "Quedan pocas piezas"
                          : undefined
                    }
                  >
                    {producto.stock}
                  </span>
                )}
              </td>

              <td className="px-3 py-2 align-top">
                <div className="flex justify-end gap-1">
                  {enEdicion ? (
                    <>
                      <button
                        onClick={() => guardar(producto.sku)}
                        disabled={guardando}
                        title="Guardar (Enter)"
                        aria-label="Guardar cambios"
                        className="boton boton-suave px-2 py-1"
                        style={{ color: "var(--color-acento)" }}
                      >
                        <Check size={14} />
                      </button>
                      <button
                        onClick={() => setEditando(null)}
                        title="Cancelar (Esc)"
                        aria-label="Cancelar edición"
                        className="boton boton-suave px-2 py-1"
                      >
                        <X size={14} />
                      </button>
                    </>
                  ) : (
                    <>
                      <button
                        onClick={() => abrir(producto)}
                        title="Editar precio y existencia"
                        aria-label={`Editar ${producto.nombre}`}
                        className="boton boton-suave px-2 py-1"
                      >
                        <Pencil size={14} />
                      </button>
                      {producto.activo ? (
                        <button
                          onClick={() => onEliminar(producto)}
                          title="Dar de baja"
                          aria-label={`Dar de baja ${producto.nombre}`}
                          className="boton boton-suave px-2 py-1 hover:!border-red-300 hover:!bg-red-50 hover:!text-red-600"
                        >
                          <Trash2 size={14} />
                        </button>
                      ) : (
                        <button
                          onClick={() => onReactivar(producto)}
                          title="Reactivar"
                          aria-label={`Reactivar ${producto.nombre}`}
                          className="boton boton-suave px-2 py-1"
                        >
                          <Undo2 size={14} />
                        </button>
                      )}
                    </>
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
