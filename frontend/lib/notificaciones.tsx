"use client";

/**
 * Avisos de la aplicacion, hechos a mano.
 *
 * Sin libreria externa: son ~60 lineas y una dependencia mas habria que
 * justificarla. El requisito real es que toda accion que cambia datos deje
 * constancia visible, porque en un mostrador el vendedor no puede quedarse con
 * la duda de si el cobro entro o el alta se guardo.
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";

export type TipoAviso = "exito" | "error" | "info";

export type Aviso = {
  id: number;
  tipo: TipoAviso;
  titulo: string;
  detalle?: string;
  saliendo?: boolean;
};

type Valor = {
  avisos: Aviso[];
  notificar: (tipo: TipoAviso, titulo: string, detalle?: string) => void;
  cerrar: (id: number) => void;
};

const Contexto = createContext<Valor | null>(null);

// Los errores se quedan mas tiempo: el usuario tiene que poder leer que fallo.
const DURACION: Record<TipoAviso, number> = {
  exito: 3200,
  info: 3200,
  error: 6000,
};

const MAXIMO_VISIBLE = 4;

export function NotificacionesProvider({ children }: { children: ReactNode }) {
  const [avisos, setAvisos] = useState<Aviso[]>([]);
  const siguienteId = useRef(1);
  const temporizadores = useRef<number[]>([]);

  const cerrar = useCallback((id: number) => {
    // Se marca saliendo para que corra la animacion y se retira despues; si se
    // quitara de golpe, el aviso desapareceria a tiron.
    setAvisos((actuales) =>
      actuales.map((a) => (a.id === id ? { ...a, saliendo: true } : a)),
    );
    const t = window.setTimeout(
      () => setAvisos((actuales) => actuales.filter((a) => a.id !== id)),
      150,
    );
    temporizadores.current.push(t);
  }, []);

  const notificar = useCallback(
    (tipo: TipoAviso, titulo: string, detalle?: string) => {
      const id = siguienteId.current++;
      setAvisos((actuales) => [
        ...actuales.slice(-(MAXIMO_VISIBLE - 1)),
        { id, tipo, titulo, detalle },
      ]);
      const t = window.setTimeout(() => cerrar(id), DURACION[tipo]);
      temporizadores.current.push(t);
    },
    [cerrar],
  );

  useEffect(
    () => () => temporizadores.current.forEach((t) => window.clearTimeout(t)),
    [],
  );

  return (
    <Contexto.Provider value={{ avisos, notificar, cerrar }}>
      {children}
    </Contexto.Provider>
  );
}

export function useAvisos(): Valor {
  const valor = useContext(Contexto);
  if (!valor) {
    throw new Error("useAvisos debe usarse dentro de NotificacionesProvider.");
  }
  return valor;
}
