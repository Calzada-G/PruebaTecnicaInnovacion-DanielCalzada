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
  onEliminar: (sku: string) => void;
  onReactivar: (sku: string) => void;
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
  const [borrador, setBorrador] = useState<{ precio: string; stock: string }>({
    precio: "",
    stock: "",
  });

  function abrir(producto: Producto) {
    setEditando(producto.sku);
    setBorrador({
      precio: String(producto.precio),
      stock: String(producto.stock),
    });
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

  return (
    <table className="w-full border-collapse">
      <thead>
        <tr className="border-b border-linea text-left text-xs uppercase tracking-wide text-acero">
          <th className="px-2 py-2 font-medium">Producto</th>
          <th className="px-2 py-2 font-medium">Categoria</th>
          <th className="px-2 py-2 font-medium">Uso recomendado</th>
          <th className="px-2 py-2 text-right font-medium">Precio</th>
          <th className="px-2 py-2 text-right font-medium">Stock</th>
          <th className="px-2 py-2 text-right font-medium">Acciones</th>
        </tr>
      </thead>
      <tbody>
        {productos.map((producto) => {
          const enEdicion = editando === producto.sku;
          return (
            <tr
              key={producto.sku}
              className="border-b border-linea align-middle"
              style={{ opacity: producto.activo ? 1 : 0.5 }}
            >
              <td className="px-2 py-2">
                <ProductoTile
                  sku={producto.sku}
                  nombre={producto.nombre}
                  categoria={producto.categoria}
                  material={producto.material}
                  uso={producto.uso_recomendado}
                  tamano="chico"
                />
                {!producto.activo && (
                  <span className="text-xs text-red-600">dado de baja</span>
                )}
              </td>
              <td className="px-2 py-2 text-xs text-acero">{producto.categoria}</td>
              <td className="max-w-[260px] truncate px-2 py-2 text-xs text-acero">
                {producto.uso_recomendado}
              </td>

              <td className="px-2 py-2 text-right">
                {enEdicion ? (
                  <input
                    type="number"
                    min={0}
                    step="0.01"
                    value={borrador.precio}
                    onChange={(e) =>
                      setBorrador((b) => ({ ...b, precio: e.target.value }))
                    }
                    aria-label={`Precio de ${producto.sku}`}
                    className="cifra w-24 border border-linea px-1 py-0.5 text-right"
                  />
                ) : (
                  <span className="cifra">{precio(producto.precio)}</span>
                )}
              </td>

              <td className="px-2 py-2 text-right">
                {enEdicion ? (
                  <input
                    type="number"
                    min={0}
                    step="1"
                    value={borrador.stock}
                    onChange={(e) =>
                      setBorrador((b) => ({ ...b, stock: e.target.value }))
                    }
                    aria-label={`Stock de ${producto.sku}`}
                    className="cifra w-20 border border-linea px-1 py-0.5 text-right"
                  />
                ) : (
                  <span
                    className={
                      producto.stock === 0 ? "cifra text-red-600" : "cifra"
                    }
                  >
                    {producto.stock}
                  </span>
                )}
              </td>

              <td className="px-2 py-2">
                <div className="flex justify-end gap-1">
                  {enEdicion ? (
                    <>
                      <button
                        onClick={() => guardar(producto.sku)}
                        disabled={guardando}
                        aria-label="Guardar"
                        className="border border-linea p-1"
                        style={{ color: "var(--color-acento)" }}
                      >
                        <Check size={14} />
                      </button>
                      <button
                        onClick={() => setEditando(null)}
                        aria-label="Cancelar"
                        className="border border-linea p-1 text-acero"
                      >
                        <X size={14} />
                      </button>
                    </>
                  ) : (
                    <>
                      <button
                        onClick={() => abrir(producto)}
                        aria-label={`Editar ${producto.sku}`}
                        className="border border-linea p-1 text-acero"
                      >
                        <Pencil size={14} />
                      </button>
                      {producto.activo ? (
                        <button
                          onClick={() => onEliminar(producto.sku)}
                          aria-label={`Dar de baja ${producto.sku}`}
                          className="border border-linea p-1 text-acero hover:text-red-600"
                        >
                          <Trash2 size={14} />
                        </button>
                      ) : (
                        <button
                          onClick={() => onReactivar(producto.sku)}
                          aria-label={`Reactivar ${producto.sku}`}
                          className="border border-linea p-1 text-acero"
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
