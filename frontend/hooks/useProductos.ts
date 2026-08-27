"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, type Producto } from "../lib/api";

export function useProductos(q: string, tienda: string, incluirInactivos = false) {
  return useQuery({
    queryKey: ["productos", q, tienda, incluirInactivos],
    queryFn: () => api.productos(q, tienda, incluirInactivos),
    enabled: Boolean(tienda),
  });
}

export function useProducto(sku: string | null) {
  return useQuery({
    queryKey: ["producto", sku],
    queryFn: () => api.producto(sku as string),
    enabled: Boolean(sku),
  });
}

/**
 * Altas, ediciones y bajas comparten la invalidacion.
 *
 * Se invalida "productos" y tambien "recomendaciones": dar de baja un producto
 * o dejarlo en cero tiene que sacarlo de las sugerencias del mostrador en el
 * acto, no en el siguiente refresco.
 */
export function useCatalogo() {
  const cliente = useQueryClient();
  const invalidar = () => {
    cliente.invalidateQueries({ queryKey: ["productos"] });
    cliente.invalidateQueries({ queryKey: ["producto"] });
    cliente.invalidateQueries({ queryKey: ["recomendaciones"] });
    cliente.invalidateQueries({ queryKey: ["relaciones"] });
  };

  const crear = useMutation({
    mutationFn: (datos: Omit<Producto, "activo">) => api.crearProducto(datos),
    onSuccess: invalidar,
  });

  const actualizar = useMutation({
    mutationFn: ({ sku, cambios }: { sku: string; cambios: Partial<Producto> }) =>
      api.actualizarProducto(sku, cambios),
    onSuccess: invalidar,
  });

  const eliminar = useMutation({
    mutationFn: (sku: string) => api.eliminarProducto(sku),
    onSuccess: invalidar,
  });

  return { crear, actualizar, eliminar };
}
