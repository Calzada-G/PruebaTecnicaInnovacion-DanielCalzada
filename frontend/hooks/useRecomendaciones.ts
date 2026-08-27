"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";

export function useRecomendaciones(
  sku: string | null,
  tienda: string,
  excluir: string[],
) {
  return useQuery({
    // excluir entra en la clave: al agregar una linea al ticket la respuesta
    // cambia, porque lo que ya se lleva no se vuelve a recomendar.
    queryKey: ["recomendaciones", sku, tienda, [...excluir].sort().join(",")],
    queryFn: () => api.recomendaciones(sku as string, tienda, excluir),
    enabled: Boolean(sku && tienda),
  });
}

export function useRelaciones(tipo?: string, fuente?: string) {
  return useQuery({
    queryKey: ["relaciones", tipo ?? "", fuente ?? ""],
    queryFn: () => api.relaciones(tipo, fuente),
  });
}

export function usePesos() {
  return useQuery({ queryKey: ["pesos"], queryFn: api.pesos });
}

export function useAjustarRelacion() {
  const cliente = useQueryClient();
  const invalidar = () => {
    cliente.invalidateQueries({ queryKey: ["relaciones"] });
    // Sin esto, bloquear una relacion no se notaria en el mostrador hasta
    // recargar, y el requisito es que se note sin reiniciar nada.
    cliente.invalidateQueries({ queryKey: ["recomendaciones"] });
  };

  const ajustar = useMutation({
    mutationFn: ({
      id,
      cambios,
    }: {
      id: number;
      cambios: { estado?: string; peso_manual?: number | null };
    }) => api.ajustarRelacion(id, cambios),
    onSuccess: invalidar,
  });

  const guardarPesos = useMutation({
    mutationFn: (pesos: Record<string, number>) => api.guardarPesos(pesos),
    onSuccess: () => {
      cliente.invalidateQueries({ queryKey: ["pesos"] });
      invalidar();
    },
  });

  return { ajustar, guardarPesos };
}
