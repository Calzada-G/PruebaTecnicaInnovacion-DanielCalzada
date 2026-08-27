"use client";

/**
 * Unico estado global de la aplicacion: la tienda seleccionada.
 *
 * No hay store (Redux, Zustand) porque no hay nada mas que compartir. El resto
 * del estado o es de servidor (TanStack Query) o es local a una vista. Meter un
 * store aqui seria infraestructura sin problema que resolver.
 */

import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { useQuery } from "@tanstack/react-query";
import { api, type Tienda } from "./api";

const CLAVE = "ferreteria.tienda";

type Valor = {
  tiendas: Tienda[];
  tienda: Tienda | null;
  tiendaId: string;
  seleccionar: (id: string) => void;
  cargando: boolean;
};

const Contexto = createContext<Valor | null>(null);

export function TiendaProvider({ children }: { children: ReactNode }) {
  const [tiendaId, setTiendaId] = useState("");

  const { data: tiendas = [], isLoading } = useQuery({
    queryKey: ["tiendas"],
    queryFn: api.tiendas,
    staleTime: Infinity,
  });

  // La seleccion se lee despues del montaje y no durante el render: el servidor
  // no tiene localStorage y leerlo al renderizar romperia la hidratacion.
  useEffect(() => {
    const guardada = window.localStorage.getItem(CLAVE);
    if (guardada) setTiendaId(guardada);
  }, []);

  useEffect(() => {
    if (!tiendaId && tiendas.length) setTiendaId(tiendas[0].id);
  }, [tiendaId, tiendas]);

  const tienda = tiendas.find((t) => t.id === tiendaId) ?? null;

  // El acento de toda la interfaz cuelga de :root, asi que basta una variable
  // para que cambien botones, bordes y foco al cambiar de plaza.
  useEffect(() => {
    if (tienda) {
      document.documentElement.style.setProperty("--acento-tienda", tienda.acento);
    }
  }, [tienda]);

  function seleccionar(id: string) {
    setTiendaId(id);
    window.localStorage.setItem(CLAVE, id);
  }

  return (
    <Contexto.Provider
      value={{ tiendas, tienda, tiendaId, seleccionar, cargando: isLoading }}
    >
      {children}
    </Contexto.Provider>
  );
}

export function useTienda(): Valor {
  const valor = useContext(Contexto);
  if (!valor) throw new Error("useTienda debe usarse dentro de TiendaProvider.");
  return valor;
}
