"use client";

/**
 * Lo que el sistema detecta por su cuenta en la plaza seleccionada.
 *
 * Componente de presentacion puro: todo lo que muestra lo calcula el backend
 * en services/diagnostico_service.py. Aqui no hay ninguna regla de negocio, ni
 * un caso especial para Merida: si esa plaza sale distinta es porque no tiene
 * tickets, y eso lo dice el dato, no este archivo.
 *
 * Va en una banda horizontal bajo la cabecera y no en una columna lateral: en
 * columna, los hallazgos obligaban a scrollear dentro de una caja estrecha y
 * dejaban media cabecera de espacio muerto al lado.
 *
 * Se puede ocultar. Son avisos, no una tarea: quien ya los vio no deberia
 * volver a tenerlos delante cada vez que entra, y menos con un cliente
 * enfrente. La preferencia se recuerda por navegador.
 */

import { useEffect, useState } from "react";
import {
  AlertTriangle,
  Eye,
  EyeOff,
  Info,
  Sparkles,
  Stethoscope,
} from "lucide-react";
import type { Hallazgo } from "../lib/api";

type Props = {
  nombreTienda: string;
  hallazgos: Hallazgo[];
  ticketsEnLaPlaza: number;
  cargando: boolean;
  /** La revision no llego. Callarlo dejaria el panel diciendo "nada que
   *  reportar", que es justo lo contrario de lo que pasa. */
  fallo: boolean;
};

const ESTILO = {
  alerta: { color: "var(--color-error)", icono: AlertTriangle },
  aviso: { color: "var(--color-alerta)", icono: Info },
  oportunidad: { color: "var(--color-exito)", icono: Sparkles },
} as const;

const CLAVE = "ferreteria.mejoras-ocultas";

// Con cuatro tarjetas por fila no cabe la lista entera de SKUs, y tampoco hace
// falta: el panel dice que revisar, el detalle esta en la tabla de abajo.
const MAXIMO_CHIPS = 4;

export function PanelDiagnostico({
  nombreTienda,
  hallazgos,
  ticketsEnLaPlaza,
  cargando,
  fallo,
}: Props) {
  // Se lee despues de montar y no durante el render: el servidor no tiene
  // localStorage y leerlo al renderizar romperia la hidratacion.
  const [oculto, setOculto] = useState(false);
  useEffect(() => {
    setOculto(window.localStorage.getItem(CLAVE) === "1");
  }, []);

  function alternar() {
    setOculto((antes) => {
      window.localStorage.setItem(CLAVE, antes ? "0" : "1");
      return !antes;
    });
  }

  const resumen = fallo
    ? "No se pudo revisar: la API no respondió."
    : cargando
      ? "Revisando ventas, existencias y catálogo…"
      : ticketsEnLaPlaza === 0
        ? "Esta sucursal no tiene ventas registradas: el sistema revisa el catálogo y el clima de la zona."
        : `Sobre ${ticketsEnLaPlaza} ${ticketsEnLaPlaza === 1 ? "ticket" : "tickets"} cobrados aquí y el catálogo compartido.`;

  if (oculto) {
    return (
      <button
        onClick={alternar}
        className="boton tarjeta flex items-center gap-2 self-start px-3 py-2 text-xs text-acero hover:text-tinta"
      >
        <Eye size={14} aria-hidden />
        Mostrar qué mejorar en {nombreTienda || "esta plaza"}
        {hallazgos.length > 0 && (
          <span className="cifra font-medium text-tinta">{hallazgos.length}</span>
        )}
      </button>
    );
  }

  return (
    <section className="tarjeta p-4">
      <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
        <div className="min-w-0">
          <h2 className="flex items-center gap-1.5 text-sm font-semibold">
            <Stethoscope
              size={15}
              style={{ color: "var(--color-acento)" }}
              aria-hidden
            />
            Qué mejorar en {nombreTienda || "esta plaza"}
          </h2>
          <p className="mt-0.5 text-xs text-acero">{resumen}</p>
        </div>
        <button
          onClick={alternar}
          className="boton boton-suave flex shrink-0 items-center gap-1.5 px-2.5 py-1 text-xs"
        >
          <EyeOff size={13} aria-hidden />
          Ocultar
        </button>
      </div>

      {!cargando && !fallo && hallazgos.length === 0 && (
        <p className="mt-3 text-xs text-acero">
          Nada que reportar: no hay agotados, todo el catálogo tiene ventas y
          cada producto tiene algo que ofrecer al lado.
        </p>
      )}

      <div className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
        {hallazgos.map((hallazgo) => {
          const estilo = ESTILO[hallazgo.nivel];
          const Icono = estilo.icono;
          const chips = hallazgo.productos.slice(0, MAXIMO_CHIPS);
          const restantes = hallazgo.total - chips.length;
          return (
            <article
              key={hallazgo.clave}
              className="tarjeta tarjeta-activa aparece flex flex-col gap-1 py-2 pl-2.5 pr-2.5"
              // Una barra de color en el canto en vez de tintar la tarjeta
              // entera: con cuatro seguidas, cuatro bloques de color compiten
              // con la tabla y ninguno destaca.
              style={{ borderLeft: `3px solid ${estilo.color}` }}
            >
              <h3 className="flex items-start gap-1.5 text-[12px] font-semibold leading-tight">
                <Icono
                  size={13}
                  className="mt-px shrink-0"
                  style={{ color: estilo.color }}
                  aria-hidden
                />
                <span className="recorta-2 min-w-0">{hallazgo.titulo}</span>
              </h3>

              <p
                className="recorta-2 text-[11px] leading-snug text-acero"
                title={hallazgo.detalle}
              >
                {hallazgo.detalle}
              </p>

              {chips.length > 0 && (
                <div className="flex flex-wrap items-center gap-1">
                  {chips.map((producto) => (
                    <span
                      key={producto.sku}
                      title={producto.nombre}
                      className="cifra rounded bg-papel px-1 py-px text-[10px] text-acero"
                    >
                      {producto.sku}
                    </span>
                  ))}
                  {restantes > 0 && (
                    <span className="cifra text-[10px] text-acero">+{restantes}</span>
                  )}
                </div>
              )}

              {/* mt-auto: la acción queda a la misma altura en las cuatro
                  tarjetas aunque los textos de arriba midan distinto. */}
              <p
                className="recorta-2 mt-auto border-t border-linea pt-1.5 text-[11px] font-medium leading-snug"
                style={{ color: estilo.color }}
                title={hallazgo.accion}
              >
                {hallazgo.accion}
              </p>
            </article>
          );
        })}
      </div>
    </section>
  );
}
