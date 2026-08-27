"use client";

import { useTienda } from "../lib/tienda-context";

export default function Mostrador() {
  const { tienda, cargando } = useTienda();

  if (cargando) return <p className="text-acero">Cargando...</p>;

  return (
    <p className="text-acero">
      Mostrador de {tienda?.nombre ?? "sin tienda"} (perfil {tienda?.perfil}).
    </p>
  );
}
