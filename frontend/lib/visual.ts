/**
 * Representacion visual determinista de un producto: icono + color, sin fotos.
 *
 * No se usan imagenes de catalogo ni APIs de fotos aleatorias a proposito. La
 * tesis del proyecto es que el material y el ambiente de uso son lo que decide
 * la recomendacion; una foto generica que no corresponde al material la
 * contradice y ensena al vendedor a ignorar la diferencia que importa.
 *
 * El color del chip codifica el ambiente, que es exactamente el eje sobre el
 * que el sistema propone sustitutos.
 */

import {
  Bolt,
  Cable,
  Drill,
  Droplet,
  Flame,
  HardHat,
  Layers,
  Lock,
  Package,
  Paintbrush,
  Wrench,
  type LucideIcon,
} from "lucide-react";

const ICONOS: Record<string, LucideIcon> = {
  herramienta: Flame,
  "herramienta eléctrica": Drill,
  consumible: Package,
  fijación: Bolt,
  material: Layers,
  plomería: Droplet,
  pintura: Paintbrush,
  EPP: HardHat,
  eléctrico: Cable,
  seguridad: Lock,
};

export function iconoDe(categoria: string): LucideIcon {
  return ICONOS[categoria] ?? Wrench;
}

export type Ambiente = "costero" | "sol" | "humedad" | "interior" | "neutro";

/**
 * Misma clasificacion que perfiles.py en el backend, replicada para pintar.
 *
 * Duplicar esta regla es deliberado: el backend decide QUE recomendar y el
 * front solo decide de que color pintarlo. Exponerla por la API obligaria a
 * inventar un endpoint fuera del contrato para un detalle de presentacion.
 */
export function ambienteDe(material: string, uso: string): Ambiente {
  const texto = `${uso} ${material}`
    .toLowerCase()
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "");

  if (texto.includes("protegido")) return "interior";
  if (/costero|salin|marino|316/.test(texto)) return "costero";
  if (/solar|\buv\b/.test(texto)) return "sol";
  if (/humedad|galvaniz|intemperie|uso rudo/.test(texto)) return "humedad";
  if (texto.includes("interior")) return "interior";
  if (texto.includes("exterior")) return "humedad";
  return "neutro";
}

export const AMBIENTE: Record<Ambiente, { etiqueta: string; color: string }> = {
  costero: { etiqueta: "costero salino", color: "#0E7C86" },
  sol: { etiqueta: "sol directo", color: "#C87A0A" },
  humedad: { etiqueta: "humedad", color: "#2563EB" },
  interior: { etiqueta: "interior", color: "#6B7280" },
  neutro: { etiqueta: "uso general", color: "#94A3B8" },
};

export function precio(valor: number): string {
  return valor.toLocaleString("es-MX", {
    style: "currency",
    currency: "MXN",
    minimumFractionDigits: 0,
  });
}

/** Etiqueta de procedencia que se muestra en cada tarjeta de recomendacion. */
export function etiquetaFuente(fuente: string, soporte: number | null): string {
  if (soporte && soporte > 0) {
    return `${soporte} ${soporte === 1 ? "ticket" : "tickets"}`;
  }
  if (fuente === "atributos") return "por atributos";
  if (fuente === "manual") return "manual";
  return fuente;
}
