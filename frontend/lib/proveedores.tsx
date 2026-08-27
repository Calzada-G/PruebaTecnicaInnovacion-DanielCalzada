"use client";

/**
 * QueryClientProvider y TiendaProvider montados juntos.
 *
 * Existe como archivo aparte para que layout.tsx siga siendo Server Component:
 * asi las fuentes y el metadata se resuelven en el servidor y solo el arbol
 * interactivo viaja como cliente.
 */

import { useState, type ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Notificaciones } from "../componentes/Notificaciones";
import { NotificacionesProvider } from "./notificaciones";
import { TiendaProvider } from "./tienda-context";

export function Proveedores({ children }: { children: ReactNode }) {
  // En useState y no como constante de modulo: una instancia por montaje evita
  // que dos pestanas o un remount compartan cache sin querer.
  const [cliente] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            // El inventario cambia con cada cobro. Lo que mantiene la UI
            // honesta no es este numero sino la invalidacion explicita tras
            // comprar; esto solo evita refetches innecesarios entre tanto.
            staleTime: 30_000,
            refetchOnWindowFocus: false,
            retry: 1,
          },
        },
      }),
  );

  return (
    <QueryClientProvider client={cliente}>
      {/* Los avisos envuelven a la tienda porque cambiar de plaza tambien avisa. */}
      <NotificacionesProvider>
        <TiendaProvider>
          {children}
          <Notificaciones />
        </TiendaProvider>
      </NotificacionesProvider>
    </QueryClientProvider>
  );
}
