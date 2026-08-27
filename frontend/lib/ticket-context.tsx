"use client";

/**
 * El ticket en curso, fuera de la vista que lo muestra.
 *
 * Vivia dentro de app/page.tsx, y con el enrutado por ficheros esa vista se
 * desmonta al ir a Catalogo: el vendedor perdia lo que llevaba cobrado solo
 * por consultar un precio o revisar una sugerencia. El layout no se desmonta
 * entre rutas, asi que el estado sobrevive aqui.
 *
 * Se vacia SOLO al cambiar de sucursal. Ahi si tiene sentido: un ticket
 * pertenece a la plaza donde se cobra y descuenta de su caja, y arrastrar
 * lineas de Cancun a Merida seria cobrar en la tienda equivocada.
 *
 * Es el segundo y ultimo estado global de la aplicacion, por la misma razon
 * que el primero: se comparte entre rutas. Todo lo demas o es de servidor
 * (TanStack Query) o es local a una vista.
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import type { CompraRespuesta, Producto } from "./api";
import { useAvisos } from "./notificaciones";
import { useTienda } from "./tienda-context";

export type LineaTicket = {
  sku: string;
  nombre: string;
  precio: number;
  cantidad: number;
  /** Existencia en el momento de agregarlo: es el tope de los botones +/-. */
  stock: number;
};

type Valor = {
  lineas: LineaTicket[];
  total: number;
  piezas: number;
  /** Ultimo cobro, para el acuse en el panel del ticket. */
  ultimo: CompraRespuesta | null;
  error: string | null;
  agregar: (producto: Producto) => void;
  cambiarCantidad: (sku: string, cantidad: number) => void;
  quitar: (sku: string) => void;
  registrarCobro: (respuesta: CompraRespuesta) => void;
  registrarError: (mensaje: string | null) => void;
};

const Contexto = createContext<Valor | null>(null);

export function TicketProvider({ children }: { children: ReactNode }) {
  const { tiendaId } = useTienda();
  const { notificar } = useAvisos();
  const [lineas, setLineas] = useState<LineaTicket[]>([]);
  const [ultimo, setUltimo] = useState<CompraRespuesta | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Vaciar sin decir nada pareceria un fallo. Se lee de una referencia y no
  // del estado para que el efecto siga dependiendo solo de la sucursal.
  const enCurso = useRef(0);
  enCurso.current = lineas.length;

  useEffect(() => {
    if (enCurso.current) {
      notificar(
        "info",
        "El ticket se vació",
        "Un ticket pertenece a la sucursal donde se cobra, así que no se arrastra a otra plaza.",
      );
    }
    setLineas([]);
    setUltimo(null);
    setError(null);
  }, [tiendaId, notificar]);

  // Cerrar la pestana con un ticket a medias pierde el trabajo del vendedor y
  // el cliente sigue enfrente. El navegador solo permite pedir confirmacion.
  useEffect(() => {
    if (lineas.length === 0) return;
    function alSalir(evento: BeforeUnloadEvent) {
      evento.preventDefault();
    }
    window.addEventListener("beforeunload", alSalir);
    return () => window.removeEventListener("beforeunload", alSalir);
  }, [lineas.length]);

  // Los avisos se emiten FUERA del actualizador de estado. Dentro, React
  // ejecuta la funcion durante el render y notificar() tocaria el estado de
  // otro componente en ese momento: error en desarrollo y render incoherente.
  const agregar = useCallback(
    (producto: Producto) => {
      if (producto.stock === 0) {
        notificar("error", "Agotado", `${producto.nombre} no tiene existencia.`);
        return;
      }

      const previa = lineas.find((l) => l.sku === producto.sku);
      if (previa && previa.cantidad >= producto.stock) {
        notificar(
          "error",
          "No hay más existencia",
          `Solo quedan ${producto.stock} de ${producto.nombre}.`,
        );
        return;
      }

      setError(null);
      setUltimo(null);
      setLineas((actuales) =>
        previa
          ? actuales.map((l) =>
              l.sku === producto.sku ? { ...l, cantidad: l.cantidad + 1 } : l,
            )
          : [
              ...actuales,
              {
                sku: producto.sku,
                nombre: producto.nombre,
                precio: producto.precio,
                cantidad: 1,
                stock: producto.stock,
              },
            ],
      );
      notificar(
        "exito",
        previa ? "Una pieza más" : "Agregado al ticket",
        producto.nombre,
      );
    },
    [lineas, notificar],
  );

  const quitar = useCallback(
    (sku: string) => {
      const fuera = lineas.find((l) => l.sku === sku);
      if (!fuera) return;
      setLineas((actuales) => actuales.filter((l) => l.sku !== sku));
      notificar("info", "Quitado del ticket", fuera.nombre);
    },
    [lineas, notificar],
  );

  const cambiarCantidad = useCallback(
    (sku: string, cantidad: number) => {
      if (cantidad <= 0) {
        quitar(sku);
        return;
      }
      setLineas((actuales) =>
        actuales.map((l) =>
          l.sku === sku ? { ...l, cantidad: Math.min(cantidad, l.stock) } : l,
        ),
      );
    },
    [quitar],
  );

  const registrarCobro = useCallback((respuesta: CompraRespuesta) => {
    setUltimo(respuesta);
    setLineas([]);
    setError(null);
  }, []);

  const valor = useMemo<Valor>(
    () => ({
      lineas,
      total: lineas.reduce((suma, l) => suma + l.precio * l.cantidad, 0),
      piezas: lineas.reduce((suma, l) => suma + l.cantidad, 0),
      ultimo,
      error,
      agregar,
      cambiarCantidad,
      quitar,
      registrarCobro,
      registrarError: setError,
    }),
    [lineas, ultimo, error, agregar, cambiarCantidad, quitar, registrarCobro],
  );

  return <Contexto.Provider value={valor}>{children}</Contexto.Provider>;
}

export function useTicket(): Valor {
  const valor = useContext(Contexto);
  if (!valor) throw new Error("useTicket debe usarse dentro de TicketProvider.");
  return valor;
}
