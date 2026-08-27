/**
 * Unico cliente HTTP de la aplicacion.
 *
 * Ningun componente hace fetch por su cuenta: si el manejo de errores o la URL
 * base vivieran repartidos, el mensaje "Quedan 3" del mostrador dependeria de
 * quien escribio cada llamada.
 */

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type Tienda = {
  id: string;
  nombre: string;
  perfil: string;
  acento: string;
};

export type Producto = {
  sku: string;
  nombre: string;
  descripcion: string;
  categoria: string;
  material: string;
  uso_recomendado: string;
  precio: number;
  stock: number;
  activo: boolean;
};

export type Candidato = {
  sku: string;
  tipo: "complemento" | "sustituto";
  score: number;
  fuente: string;
  justificacion: string;
  soporte: number | null;
  confianza: number | null;
  lift: number | null;
};

type Recomendacion = {
  sustituto: Candidato | null;
  complementos: Candidato[];
};

/** Linea ya cobrada, tal como la devuelve la API. No es la del ticket en
 *  curso: esa vive en lib/ticket-context y todavia no tiene subtotal ni
 *  stock restante porque nadie la ha descontado. */
export type LineaCobrada = {
  sku: string;
  nombre: string;
  cantidad: number;
  precio_unitario: number;
  subtotal: number;
  stock_restante: number;
};

export type CompraRespuesta = {
  ticket_id: string;
  tienda: string;
  fecha: string;
  lineas: LineaCobrada[];
  total: number;
  repetida: boolean;
};

export type Relacion = {
  id: number;
  sku_origen: string;
  sku_destino: string;
  tipo: "complemento" | "sustituto";
  fuente: string;
  score: number;
  soporte: number | null;
  confianza: number | null;
  lift: number | null;
  justificacion: string;
  justificacion_ia: string | null;
  estado: "activa" | "bloqueada" | "fijada";
  peso_manual: number | null;
  nombre_origen: string;
  nombre_destino: string;
  stock_destino: number;
  activo_destino: boolean;
};

/** Un problema o una oportunidad que el sistema detecta solo, sin que nadie
 *  lo capture: falta de historico, agotados, huecos del catalogo por plaza. */
export type Hallazgo = {
  clave: string;
  nivel: "alerta" | "aviso" | "oportunidad";
  titulo: string;
  detalle: string;
  accion: string;
  /** Productos afectados en total; `productos` trae solo los primeros. */
  total: number;
  productos: { sku: string; nombre: string }[];
};

export type Diagnostico = {
  tienda: string;
  nombre: string;
  perfil: string;
  tickets_en_la_plaza: number;
  tickets_en_la_cadena: number;
  productos_activos: number;
  hallazgos: Hallazgo[];
};

export type PuntoAnalisis = {
  titulo: string;
  analisis: string;
  dato: string;
  impacto: "alto" | "medio" | "bajo";
  skus: string[];
};

export type Analisis = {
  resumen: string;
  negocio: PuntoAnalisis[];
  sistema: PuntoAnalisis[];
  decisiones: { titulo: string; porque: string; accion: string }[];
};

export type RespuestaAnalisis = {
  tienda: string;
  /** Hay clave de IA configurada. Sin ella el resto del sistema va igual. */
  disponible: boolean;
  hay_analisis: boolean;
  /** Identifica el estado del sistema ahora: catálogo, ventas, relaciones. */
  huella_actual: string;
  /** El análisis guardado describe el sistema actual: no hay nada nuevo. */
  vigente: boolean;
  desde_cache: boolean;
  analisis: Analisis | null;
  modelo: string | null;
  generado_en: string | null;
  huella: string | null;
};

/** Error de negocio con los datos que el mostrador necesita para el mensaje. */
export class ErrorApi extends Error {
  estado: number;
  sku?: string;
  disponible?: number | null;

  constructor(
    mensaje: string,
    estado: number,
    extra?: { sku?: string; disponible?: number | null },
  ) {
    super(mensaje);
    this.estado = estado;
    this.sku = extra?.sku;
    this.disponible = extra?.disponible;
  }
}

async function pedir<T>(ruta: string, opciones: RequestInit = {}): Promise<T> {
  let respuesta: Response;
  try {
    respuesta = await fetch(`${BASE}${ruta}`, {
      ...opciones,
      headers: { "Content-Type": "application/json", ...opciones.headers },
    });
  } catch {
    throw new ErrorApi(
      "No hay conexion con el servidor. Revisa que la API este corriendo.",
      0,
    );
  }

  if (respuesta.status === 204) return undefined as T;

  const cuerpo = await respuesta.json().catch(() => null);

  if (!respuesta.ok) {
    const detalle = cuerpo?.detail;
    // Los 422 de Pydantic traen una lista de errores, no un texto.
    const mensaje =
      typeof detalle === "string"
        ? detalle
        : Array.isArray(detalle)
          ? detalle.map((e: { msg: string }) => e.msg).join(". ")
          : "La operacion no se pudo completar.";
    throw new ErrorApi(mensaje, respuesta.status, {
      sku: cuerpo?.sku,
      disponible: cuerpo?.disponible,
    });
  }

  return cuerpo as T;
}

export const api = {
  tiendas: () => pedir<Tienda[]>("/api/tiendas"),

  productos: (buscar: string, tienda: string, incluirInactivos = false) => {
    const p = new URLSearchParams();
    if (buscar) p.set("buscar", buscar);
    if (tienda) p.set("tienda", tienda);
    if (incluirInactivos) p.set("incluir_inactivos", "true");
    return pedir<Producto[]>(`/api/productos?${p}`);
  },

  producto: (sku: string) => pedir<Producto>(`/api/productos/${sku}`),

  crearProducto: (datos: Omit<Producto, "activo">) =>
    pedir<Producto>("/api/productos", {
      method: "POST",
      body: JSON.stringify(datos),
    }),

  actualizarProducto: (sku: string, cambios: Partial<Producto>) =>
    pedir<Producto>(`/api/productos/${sku}`, {
      method: "PATCH",
      body: JSON.stringify(cambios),
    }),

  eliminarProducto: (sku: string) =>
    pedir<void>(`/api/productos/${sku}`, { method: "DELETE" }),

  recomendaciones: (sku: string, tienda: string, excluir: string[]) => {
    const p = new URLSearchParams({ sku, tienda });
    if (excluir.length) p.set("excluir", excluir.join(","));
    return pedir<Recomendacion>(`/api/recomendaciones?${p}`);
  },

  diagnostico: (tienda: string) =>
    pedir<Diagnostico>(`/api/diagnostico?${new URLSearchParams({ tienda })}`),

  analisisGuardado: (tienda: string) =>
    pedir<RespuestaAnalisis>(`/api/analisis?${new URLSearchParams({ tienda })}`),

  analizar: (tienda: string) =>
    pedir<RespuestaAnalisis>("/api/analisis", {
      method: "POST",
      body: JSON.stringify({ tienda }),
    }),

  comprar: (
    tienda: string,
    items: { sku: string; cantidad: number }[],
    claveIdempotencia: string,
  ) =>
    pedir<CompraRespuesta>("/api/compras", {
      method: "POST",
      headers: { "Idempotency-Key": claveIdempotencia },
      body: JSON.stringify({ tienda, items }),
    }),

  relaciones: (tipo?: string, fuente?: string) => {
    const p = new URLSearchParams();
    if (tipo) p.set("tipo", tipo);
    if (fuente) p.set("fuente", fuente);
    return pedir<Relacion[]>(`/api/relaciones?${p}`);
  },

  ajustarRelacion: (
    id: number,
    cambios: { estado?: string; peso_manual?: number | null },
  ) =>
    pedir<Relacion>(`/api/relaciones/${id}`, {
      method: "PATCH",
      body: JSON.stringify(cambios),
    }),

  pesos: () => pedir<Record<string, number>>("/api/config/pesos"),

  guardarPesos: (pesos: Record<string, number>) =>
    pedir<Record<string, number>>("/api/config/pesos", {
      method: "PUT",
      body: JSON.stringify({ pesos }),
    }),
};
