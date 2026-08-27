"use client";

/**
 * Cabecera fija: conmutador de vistas + selector de tienda.
 *
 * En la estructura con Vite esto vivia en App.tsx junto al useState que
 * conmutaba las vistas. Con Next el enrutado por ficheros sustituye ese
 * useState, pero marcar la vista activa necesita usePathname, que es un hook
 * de cliente, y layout.tsx se queda como Server Component para resolver las
 * fuentes y el metadata en el servidor.
 */

import Link from "next/link";
import { usePathname } from "next/navigation";
import { SelectorTienda } from "./SelectorTienda";

const VISTAS = [
  { href: "/", etiqueta: "Mostrador" },
  { href: "/catalogo", etiqueta: "Catalogo" },
  { href: "/relaciones", etiqueta: "Relaciones" },
];

export function Navegacion() {
  const ruta = usePathname();

  return (
    <header className="border-b border-linea bg-white">
      <div className="mx-auto flex max-w-[1400px] items-center justify-between gap-4 px-4 py-2">
        <nav className="flex items-center gap-1">
          {VISTAS.map((vista) => {
            const activa = ruta === vista.href;
            return (
              <Link
                key={vista.href}
                href={vista.href}
                aria-current={activa ? "page" : undefined}
                className="border-b-2 px-3 py-1 font-medium transition-colors"
                style={{
                  borderColor: activa ? "var(--color-acento)" : "transparent",
                  color: activa ? "var(--color-acento)" : "var(--color-acero)",
                }}
              >
                {vista.etiqueta}
              </Link>
            );
          })}
        </nav>
        <SelectorTienda />
      </div>
    </header>
  );
}
