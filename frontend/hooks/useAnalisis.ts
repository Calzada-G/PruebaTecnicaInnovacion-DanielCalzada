"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";

/**
 * El analisis guardado. Nunca consulta al modelo.
 *
 * Trae `vigente`, que dice si ese analisis sigue describiendo el sistema
 * actual. Es lo que apaga el boton cuando no hay nada nuevo que analizar.
 */
export function useAnalisis(tienda: string) {
  return useQuery({
    queryKey: ["analisis", tienda],
    queryFn: () => api.analisisGuardado(tienda),
    enabled: Boolean(tienda),
  });
}

export function useAnalizar() {
  const cliente = useQueryClient();
  return useMutation({
    mutationFn: (tienda: string) => api.analizar(tienda),
    onSuccess: (datos) =>
      cliente.setQueryData(["analisis", datos.tienda], datos),
  });
}
