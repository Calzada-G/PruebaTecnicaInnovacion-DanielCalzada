"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api, type CompraRespuesta } from "../lib/api";

export function useCompra() {
  const cliente = useQueryClient();

  return useMutation<
    CompraRespuesta,
    Error,
    { tienda: string; items: { sku: string; cantidad: number }[] }
  >({
    mutationFn: ({ tienda, items }) =>
      // La clave se genera por intento de cobro. Si el vendedor pulsa Cobrar
      // dos veces o la red reintenta, el backend reconoce la clave y devuelve
      // el ticket original en vez de descontar dos veces.
      api.comprar(tienda, items, crypto.randomUUID()),

    onSuccess: () => {
      // Invalidacion explicita y no cosmetica: sin esto la interfaz seguiria
      // mostrando el stock anterior y podria ofrecer un producto que se acaba
      // de agotar, rompiendo el requisito de no recomendar sin existencia.
      cliente.invalidateQueries({ queryKey: ["productos"] });
      cliente.invalidateQueries({ queryKey: ["producto"] });
      cliente.invalidateQueries({ queryKey: ["recomendaciones"] });
      // Cobrar cambia existencias y ventas por plaza: las dos cosas que
      // el diagnostico del catalogo esta mirando.
      cliente.invalidateQueries({ queryKey: ["diagnostico"] });
    },
  });
}
