"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";

/**
 * Que le falta a la sucursal seleccionada.
 *
 * Se invalida al cobrar y al tocar el catalogo (useCompra y useCatalogo): un
 * diagnostico que sigue diciendo "3 sin existencia" despues de reponerlas
 * enseña al encargado a ignorarlo.
 */
export function useDiagnostico(tienda: string) {
  return useQuery({
    queryKey: ["diagnostico", tienda],
    queryFn: () => api.diagnostico(tienda),
    enabled: Boolean(tienda),
  });
}
