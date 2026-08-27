"use client";

import { useState } from "react";
import { Plus } from "lucide-react";
import { TablaCatalogo } from "../../componentes/TablaCatalogo";
import { useCatalogo, useProductos } from "../../hooks/useProductos";
import { ErrorApi, type Producto } from "../../lib/api";
import { useTienda } from "../../lib/tienda-context";

const VACIO = {
  sku: "",
  nombre: "",
  descripcion: "",
  categoria: "",
  material: "",
  uso_recomendado: "",
  precio: "",
  stock: "",
};

export default function Catalogo() {
  const { tiendaId } = useTienda();
  const [consulta, setConsulta] = useState("");
  const [alta, setAlta] = useState(false);
  const [borrador, setBorrador] = useState(VACIO);
  const [error, setError] = useState<string | null>(null);

  // El catalogo del negocio si muestra las bajas: hay que poder revertirlas.
  const { data: productos = [], isLoading } = useProductos(consulta, tiendaId, true);
  const { crear, actualizar, eliminar } = useCatalogo();

  async function guardarAlta(evento: React.FormEvent) {
    evento.preventDefault();
    setError(null);
    try {
      await crear.mutateAsync({
        ...borrador,
        precio: Number(borrador.precio),
        stock: Number(borrador.stock),
      } as Omit<Producto, "activo">);
      setBorrador(VACIO);
      setAlta(false);
    } catch (excepcion) {
      setError(
        excepcion instanceof ErrorApi ? excepcion.message : "No se pudo crear.",
      );
    }
  }

  function editar(sku: string, cambios: Partial<Producto>) {
    setError(null);
    actualizar.mutate(
      { sku, cambios },
      {
        onError: (e) =>
          setError(e instanceof ErrorApi ? e.message : "No se pudo guardar."),
      },
    );
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <input
          value={consulta}
          onChange={(e) => setConsulta(e.target.value)}
          placeholder="Filtrar catalogo"
          aria-label="Filtrar catalogo"
          className="w-72 border border-linea bg-white px-2 py-1 outline-none"
        />
        <button
          onClick={() => setAlta((v) => !v)}
          className="flex items-center gap-1 px-3 py-1.5 font-medium text-white"
          style={{ background: "var(--color-acento)" }}
        >
          <Plus size={14} /> Nuevo producto
        </button>
      </div>

      {error && (
        <p className="border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
          {error}
        </p>
      )}

      {alta && (
        <form
          onSubmit={guardarAlta}
          className="grid gap-2 border border-linea bg-white p-3 sm:grid-cols-2 lg:grid-cols-4"
        >
          {(
            [
              ["sku", "SKU", "text"],
              ["nombre", "Nombre", "text"],
              ["categoria", "Categoria", "text"],
              ["material", "Material", "text"],
              ["uso_recomendado", "Uso recomendado", "text"],
              ["descripcion", "Descripcion", "text"],
              ["precio", "Precio", "number"],
              ["stock", "Stock", "number"],
            ] as const
          ).map(([campo, etiqueta, tipo]) => (
            <label key={campo} className="flex flex-col gap-1 text-xs text-acero">
              {etiqueta}
              <input
                type={tipo}
                min={tipo === "number" ? 0 : undefined}
                required={["sku", "nombre", "categoria", "precio", "stock"].includes(
                  campo,
                )}
                value={borrador[campo]}
                onChange={(e) =>
                  setBorrador((b) => ({ ...b, [campo]: e.target.value }))
                }
                className="border border-linea px-2 py-1 text-sm text-tinta outline-none"
              />
            </label>
          ))}
          <div className="flex items-end gap-2">
            <button
              type="submit"
              disabled={crear.isPending}
              className="px-3 py-1.5 font-medium text-white disabled:opacity-40"
              style={{ background: "var(--color-acento)" }}
            >
              {crear.isPending ? "Creando..." : "Crear"}
            </button>
            <button
              type="button"
              onClick={() => setAlta(false)}
              className="border border-linea px-3 py-1.5 text-acero"
            >
              Cancelar
            </button>
          </div>
        </form>
      )}

      <div className="overflow-x-auto border border-linea bg-white">
        {isLoading ? (
          <p className="p-3 text-acero">Cargando catalogo...</p>
        ) : (
          <TablaCatalogo
            productos={productos}
            onGuardar={editar}
            onEliminar={(sku) => eliminar.mutate(sku)}
            onReactivar={(sku) => editar(sku, { activo: true })}
            guardando={actualizar.isPending}
          />
        )}
      </div>

      <p className="text-xs text-acero">
        La baja es logica: el producto deja de venderse y de recomendarse, pero
        conserva su historial de ventas y se puede reactivar.
      </p>
    </div>
  );
}
