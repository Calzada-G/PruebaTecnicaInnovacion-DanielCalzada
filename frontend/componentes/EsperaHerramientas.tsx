"use client";

/**
 * Estado de espera del mostrador: herramientas en gris que se mueven despacio.
 *
 * Gris y lento a proposito. Es un fondo, no un contenido: si compitiera por la
 * atencion con el buscador estaria estorbando en la unica pantalla donde el
 * usuario tiene un cliente enfrente. Desaparece en cuanto se elige un producto.
 *
 * Sin imagenes, como el resto de la interfaz: iconos de la misma familia que
 * los del catalogo, para que no parezcan de otra aplicacion.
 */

import { Bolt, Drill, Hammer, HardHat, Paintbrush, Ruler, Wrench } from "lucide-react";

const HERRAMIENTAS = [Wrench, Drill, Hammer, Bolt, Paintbrush, Ruler, HardHat];

export function EsperaHerramientas() {
  return (
    <div
      className="flex select-none flex-col items-center justify-center gap-4 py-10"
      aria-hidden
    >
      <div className="flex items-end gap-5 sm:gap-8">
        {HERRAMIENTAS.map((Icono, indice) => (
          <span
            key={indice}
            className="flota"
            style={{
              // Escalonado: si flotaran a la vez pareceria un parpadeo del
              // navegador en vez de un movimiento.
              animationDelay: `${indice * 0.35}s`,
              color: "var(--color-acero)",
              opacity: 0.28,
            }}
          >
            <Icono size={indice % 2 === 0 ? 30 : 24} strokeWidth={1.5} />
          </span>
        ))}
      </div>

      {/* Una linea que se recorre sola: da la sensacion de proceso en marcha
          sin prometer que algo se este cargando de verdad. */}
      <div className="riel h-px w-56 max-w-full sm:w-72" />

      <p className="text-xs text-acero">Esperando el primer producto del ticket</p>
    </div>
  );
}
