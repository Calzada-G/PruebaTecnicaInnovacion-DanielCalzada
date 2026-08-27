"use client";

import { useState } from "react";
import { Plus, Search, X } from "lucide-react";
import { TablaCatalogo } from "../../componentes/TablaCatalogo";
import { useCatalogo, useProductos } from "../../hooks/useProductos";
import { ErrorApi, type Producto } from "../../lib/api";
import { useAvisos } from "../../lib/notificaciones";
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

const CAMPOS = [
  { id: "sku", etiqueta: "SKU", tipo: "text", req: true, ayuda: "Ej. SKU029" },
  { id: "nombre", etiqueta: "Nombre", tipo: "text", req: true, ayuda: "" },
  {
    id: "categoria",
    etiqueta: "Categoría",
    tipo: "text",
    req: true,
    ayuda: "herramienta, consumible, EPP…",
  },
  {
    id: "material",
    etiqueta: "Material",
    tipo: "text",
    req: false,
    ayuda: "Define el color del chip",
  },
  {
    id: "uso_recomendado",
    etiqueta: "Uso recomendado",
    tipo: "text",
    req: false,
    ayuda: "De aquí salen las sugerencias",
  },
  { id: "descripcion", etiqueta: "Descripción", tipo: "text", req: false, ayuda: "" },
  { id: "precio", etiqueta: "Precio", tipo: "number", req: true, ayuda: "" },
  { id: "stock", etiqueta: "Existencia", tipo: "number", req: true, ayuda: "" },
] as const;

export default function Catalogo() {
  const { tiendaId } = useTienda();
  const { notificar } = useAvisos();
  const [consulta, setConsulta] = useState("");
  const [alta, setAlta] = useState(false);
  const [borrador, setBorrador] = useState(VACIO);
  const [porBorrar, setPorBorrar] = useState<Producto | null>(null);

  // El catalogo del negocio SI muestra las bajas: si el borrado es logico,
  // revertirlo tiene que ser operable.
  const { data: productos = [], isLoading } = useProductos(consulta, tiendaId, true);
  const { crear, actualizar, eliminar } = useCatalogo();

  const activos = productos.filter((p) => p.activo).length;
  const agotados = productos.filter((p) => p.activo && p.stock === 0).length;

  async function guardarAlta(evento: React.FormEvent) {
    evento.preventDefault();
    try {
      const creado = await crear.mutateAsync({
        ...borrador,
        precio: Number(borrador.precio),
        stock: Number(borrador.stock),
      } as Omit<Producto, "activo">);
      setBorrador(VACIO);
      setAlta(false);
      notificar(
        "exito",
        "Producto creado",
        `${creado.nombre} (${creado.sku}) ya se puede vender y recomendar.`,
      );
    } catch (excepcion) {
      notificar(
        "error",
        "No se pudo crear",
        excepcion instanceof ErrorApi
          ? excepcion.message
          : "Revisa los datos e intenta de nuevo.",
      );
    }
  }

  function editar(sku: string, cambios: Partial<Producto>) {
    const antes = productos.find((p) => p.sku === sku);
    actualizar.mutate(
      { sku, cambios },
      {
        onSuccess: (despues) => {
          const partes: string[] = [];
          if (antes && cambios.precio != null && cambios.precio !== antes.precio) {
            partes.push(`precio ${antes.precio} → ${despues.precio}`);
          }
          if (antes && cambios.stock != null && cambios.stock !== antes.stock) {
            partes.push(`existencia ${antes.stock} → ${despues.stock}`);
          }
          if (cambios.activo) partes.push("reactivado");
          notificar(
            "exito",
            `${despues.nombre} actualizado`,
            partes.length ? partes.join(" · ") : "Sin cambios en los valores.",
          );
        },
        onError: (e) =>
          notificar(
            "error",
            "No se pudo guardar",
            e instanceof ErrorApi ? e.message : "Intenta de nuevo.",
          ),
      },
    );
  }

  function confirmarBaja() {
    if (!porBorrar) return;
    const producto = porBorrar;
    setPorBorrar(null);
    eliminar.mutate(producto.sku, {
      onSuccess: () =>
        notificar(
          "info",
          `${producto.nombre} dado de baja`,
          "Sale del mostrador y de las recomendaciones. Su historial se conserva y puedes reactivarlo.",
        ),
      onError: (e) =>
        notificar(
          "error",
          "No se pudo dar de baja",
          e instanceof ErrorApi ? e.message : "Intenta de nuevo.",
        ),
    });
  }

  return (
    <div className="flex flex-col gap-3">
      <section className="tarjeta p-4">
        <h1 className="text-base font-semibold">Catálogo</h1>
        <p className="mt-1 max-w-3xl text-sm text-acero">
          Existencias compartidas por las 5 sucursales. Lo que cambies aquí se
          refleja de inmediato en el mostrador y en las sugerencias.
        </p>
        <p className="mt-2 text-xs text-acero">
          <span className="cifra font-medium text-tinta">{activos}</span> productos
          a la venta
          {agotados > 0 && (
            <>
              {" · "}
              <span className="cifra" style={{ color: "var(--color-alerta)" }}>
                {agotados}
              </span>{" "}
              sin existencia
            </>
          )}
          {productos.length - activos > 0 && (
            <>
              {" · "}
              <span className="cifra">{productos.length - activos}</span> dados de
              baja
            </>
          )}
        </p>
      </section>

      <div className="flex flex-wrap items-center gap-2">
        <div className="tarjeta flex items-center gap-2 px-2.5 py-1.5">
          <Search size={14} className="shrink-0 text-acero" aria-hidden />
          <input
            value={consulta}
            onChange={(e) => setConsulta(e.target.value)}
            placeholder="Filtrar por nombre, material o uso…"
            aria-label="Filtrar catálogo"
            className="w-64 min-w-0 bg-transparent outline-none placeholder:text-acero"
          />
          {consulta && (
            <button
              onClick={() => setConsulta("")}
              aria-label="Limpiar filtro"
              className="boton shrink-0 text-acero hover:text-tinta"
            >
              <X size={14} />
            </button>
          )}
        </div>
        <button
          onClick={() => setAlta((v) => !v)}
          className="boton boton-primario ml-auto flex items-center gap-1.5 px-3 py-1.5"
          aria-expanded={alta}
        >
          <Plus size={15} aria-hidden /> Nuevo producto
        </button>
      </div>

      {alta && (
        <form onSubmit={guardarAlta} className="tarjeta aparece p-4">
          <h2 className="mb-3 text-sm font-semibold">Alta de producto</h2>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {CAMPOS.map((campo) => (
              <label key={campo.id} className="flex min-w-0 flex-col gap-1">
                <span className="text-xs font-medium text-acero">
                  {campo.etiqueta}
                  {campo.req && <span style={{ color: "var(--color-error)" }}> *</span>}
                </span>
                <input
                  type={campo.tipo}
                  min={campo.tipo === "number" ? 0 : undefined}
                  step={campo.id === "precio" ? "0.01" : undefined}
                  required={campo.req}
                  value={borrador[campo.id]}
                  onChange={(e) =>
                    setBorrador((b) => ({ ...b, [campo.id]: e.target.value }))
                  }
                  className="rounded-[var(--radio)] border border-linea px-2 py-1.5 text-sm outline-none transition-colors focus:border-[var(--color-acento)]"
                />
                {campo.ayuda && (
                  <span className="text-[11px] text-acero">{campo.ayuda}</span>
                )}
              </label>
            ))}
          </div>
          <div className="mt-4 flex gap-2">
            <button
              type="submit"
              disabled={crear.isPending}
              className="boton boton-primario px-4 py-2"
            >
              {crear.isPending ? "Creando…" : "Crear producto"}
            </button>
            <button
              type="button"
              onClick={() => {
                setAlta(false);
                setBorrador(VACIO);
              }}
              className="boton boton-suave px-4 py-2"
            >
              Cancelar
            </button>
          </div>
        </form>
      )}

      {porBorrar && (
        <div
          className="tarjeta aparece flex flex-wrap items-center justify-between gap-3 p-3"
          style={{ borderColor: "#fecaca", background: "#fef2f2" }}
          role="alertdialog"
          aria-label="Confirmar baja"
        >
          <p className="min-w-0 text-sm">
            ¿Dar de baja{" "}
            <strong className="font-medium">{porBorrar.nombre}</strong>? Dejará de
            venderse y de recomendarse. Su historial se conserva.
          </p>
          <div className="flex shrink-0 gap-2">
            <button
              onClick={confirmarBaja}
              className="boton px-3 py-1.5 text-white"
              style={{ background: "var(--color-error)" }}
            >
              Sí, dar de baja
            </button>
            <button
              onClick={() => setPorBorrar(null)}
              className="boton boton-suave px-3 py-1.5"
            >
              Cancelar
            </button>
          </div>
        </div>
      )}

      <div className="tarjeta overflow-x-auto">
        {isLoading ? (
          <p className="p-4 text-sm text-acero">Cargando catálogo…</p>
        ) : productos.length === 0 ? (
          <p className="p-4 text-sm text-acero">
            Ningún producto coincide con «{consulta}».
          </p>
        ) : (
          <TablaCatalogo
            productos={productos}
            onGuardar={editar}
            onEliminar={setPorBorrar}
            onReactivar={(p) => editar(p.sku, { activo: true })}
            guardando={actualizar.isPending}
          />
        )}
      </div>
    </div>
  );
}
