"use client";

/**
 * Cabecera fija: marca, conmutador de vistas y selector de tienda.
 *
 * En la estructura con Vite esto vivia en App.tsx junto al useState que
 * conmutaba las vistas. Con Next el enrutado por ficheros lo sustituye, pero
 * marcar la vista activa necesita usePathname, que es hook de cliente, y
 * layout.tsx se queda como Server Component para las fuentes y el metadata.
 */

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Link2, Package, Receipt, Store } from "lucide-react";
import { useTicket } from "../lib/ticket-context";
import { precio } from "../lib/visual";
import { SelectorTienda } from "./SelectorTienda";

const VISTAS = [
  { href: "/", etiqueta: "Mostrador", icono: Store, ayuda: "Vender y recomendar" },
  {
    href: "/catalogo",
    etiqueta: "Catálogo",
    icono: Package,
    ayuda: "Altas, precios y existencias",
  },
  {
    href: "/relaciones",
    etiqueta: "Relaciones",
    icono: Link2,
    ayuda: "Qué sugiere el sistema y por qué",
  },
];

export function Navegacion() {
  const ruta = usePathname();
  const { piezas, total } = useTicket();

  return (
    <header className="sticky top-0 z-40 border-b border-linea bg-white/95 backdrop-blur">
      <div className="mx-auto flex max-w-[1500px] flex-wrap items-center gap-x-6 gap-y-2 px-4 py-2">
        <div className="flex min-w-0 items-center gap-2">
          <div
            className="flex size-8 shrink-0 items-center justify-center rounded-[var(--radio)] text-white"
            style={{ background: "var(--color-acento)" }}
            aria-hidden
          >
            <Store size={17} />
          </div>
          <div className="min-w-0 leading-tight">
            <div className="recorta font-semibold">Ferretería Salinas</div>
            <div className="recorta text-[11px] text-acero">
              Inventario compartido · 5 sucursales
            </div>
          </div>
        </div>

        <nav className="flex items-center gap-1" aria-label="Secciones">
          {VISTAS.map((vista) => {
            const activa = ruta === vista.href;
            const Icono = vista.icono;
            return (
              <Link
                key={vista.href}
                href={vista.href}
                aria-current={activa ? "page" : undefined}
                title={vista.ayuda}
                className="boton flex items-center gap-1.5 border-b-2 px-3 py-1.5"
                style={{
                  borderColor: activa ? "var(--color-acento)" : "transparent",
                  color: activa ? "var(--color-acento)" : "var(--color-acero)",
                  background: activa
                    ? "color-mix(in srgb, var(--color-acento) 7%, #fff)"
                    : "transparent",
                }}
              >
                <Icono size={15} aria-hidden />
                {vista.etiqueta}
              </Link>
            );
          })}
        </nav>

        <div className="ml-auto flex items-center gap-2">
          {/* El ticket sigue vivo fuera del mostrador. Sin este recordatorio,
              el vendedor no tiene forma de saberlo desde el catalogo. */}
          {piezas > 0 && ruta !== "/" && (
            <Link
              href="/"
              title="Volver al mostrador"
              className="boton aparece flex items-center gap-1.5 border px-2.5 py-1.5 text-xs"
              style={{
                borderColor: "color-mix(in srgb, var(--color-acento) 40%, #fff)",
                background: "color-mix(in srgb, var(--color-acento) 8%, #fff)",
                color: "var(--color-acento)",
              }}
            >
              <Receipt size={14} aria-hidden />
              Ticket en curso
              <span className="cifra font-medium">
                {piezas} pz · {precio(total)}
              </span>
            </Link>
          )}
          <SelectorTienda />
        </div>
      </div>
    </header>
  );
}
