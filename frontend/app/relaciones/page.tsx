"use client";

import { useMemo, useState } from "react";
import { ChevronDown, HelpCircle, Search } from "lucide-react";
import {
  AJUSTES,
  TablaRelaciones,
  ajusteDe,
  type Ajuste,
} from "../../componentes/TablaRelaciones";
import { PanelAnalisis } from "../../componentes/PanelAnalisis";
import { useAnalisis, useAnalizar } from "../../hooks/useAnalisis";
import { useProductos } from "../../hooks/useProductos";
import {
  useAjustarRelacion,
  usePesos,
  useRelaciones,
} from "../../hooks/useRecomendaciones";
import { ErrorApi, type Producto, type Relacion } from "../../lib/api";
import { useAvisos } from "../../lib/notificaciones";
import { useTienda } from "../../lib/tienda-context";

/**
 * Los pesos por fuente, expresados como la decision de negocio que representan.
 *
 * El backend guarda numeros por fuente porque es lo que el ranking necesita.
 * Pedirle a un encargado que elija "historico 1.0 / atributos 0.65" es pedirle
 * que adivine; pedirle cuanta evidencia exige para ofrecer algo es una pregunta
 * que si sabe responder.
 *
 * `efecto` no es una promesa: es lo MEDIDO sobre los 28 productos y las 5
 * plazas con estos pesos exactos. Si alguien cambia los numeros, el texto deja
 * de ser cierto y hay que volver a medir.
 */
const PREAJUSTES = [
  {
    id: "seguro",
    titulo: "Solo lo comprobado",
    texto: "Sugiere sobre todo lo que ya se ha vendido junto.",
    consecuencia: "Menos sugerencias, casi todas con ventas detrás.",
    efecto: "≈2 por producto · 76% con tickets detrás",
    pesos: { historico: 1.0, atributos: 0.35, manual: 1.5 },
  },
  {
    id: "equilibrado",
    titulo: "Equilibrado",
    texto: "Combina las ventas con el tipo de producto.",
    consecuencia: "Lo recomendado para operar el día a día.",
    efecto: "≈3 por producto · 64% con tickets detrás",
    pesos: { historico: 1.0, atributos: 0.65, manual: 1.5 },
  },
  {
    id: "descubrir",
    titulo: "Descubrir más",
    texto: "Propone también cosas que nunca se han vendido juntas.",
    consecuencia: "Más sugerencias; útil para mover catálogo parado.",
    efecto: "≈4 por producto · sin recorte",
    pesos: { historico: 0.7, atributos: 1.0, manual: 1.5 },
  },
];

function preajusteActual(pesos: Record<string, number>): string | null {
  const encontrado = PREAJUSTES.find(
    (p) =>
      Math.abs((pesos.historico ?? 0) - p.pesos.historico) < 0.01 &&
      Math.abs((pesos.atributos ?? 0) - p.pesos.atributos) < 0.01,
  );
  return encontrado?.id ?? null;
}

export default function Relaciones() {
  const { tiendaId, tienda } = useTienda();
  const { notificar } = useAvisos();
  const [tipo, setTipo] = useState("");
  const [fuente, setFuente] = useState("");
  const [busqueda, setBusqueda] = useState("");
  const [ayuda, setAyuda] = useState(false);
  const [tecnico, setTecnico] = useState(false);

  const { data: relaciones = [], isLoading } = useRelaciones(
    tipo || undefined,
    fuente || undefined,
  );
  const { data: pesos = {} } = usePesos();
  const { data: productos = [] } = useProductos("", tiendaId, true);
  const { ajustar, guardarPesos } = useAjustarRelacion();
  const { data: analisis, isLoading: cargandoAnalisis } = useAnalisis(tiendaId);
  const analizar = useAnalizar();

  const catalogo = useMemo(() => {
    const mapa = new Map<string, Producto>();
    for (const p of productos) mapa.set(p.sku, p);
    return mapa;
  }, [productos]);

  const filtradas = busqueda
    ? relaciones.filter((r) =>
        `${r.sku_origen} ${r.sku_destino} ${r.nombre_origen} ${r.nombre_destino}`
          .toLowerCase()
          .includes(busqueda.toLowerCase()),
      )
    : relaciones;

  const ocultas = relaciones.filter((r) => r.estado === "bloqueada").length;
  const fijadas = relaciones.filter((r) => r.estado === "fijada").length;
  const desdeVentas = relaciones.filter((r) => r.fuente === "historico").length;
  const activo = preajusteActual(pesos);

  function aplicarAjuste(relacion: Relacion, id: Ajuste) {
    const opcion = AJUSTES.find((a) => a.id === id);
    if (!opcion || ajusteDe(relacion) === id) return;

    ajustar.mutate(
      { id: relacion.id, cambios: opcion.cambios },
      {
        onSuccess: () =>
          notificar(
            id === "nunca" ? "info" : "exito",
            `${relacion.nombre_destino}: ${opcion.etiqueta.toLowerCase()}`,
            id === "nunca"
              ? `Ya no se ofrecerá con ${relacion.nombre_origen}. El cambio aplica en el mostrador de inmediato.`
              : `Cuando alguien lleve ${relacion.nombre_origen}, esta sugerencia ${
                  id === "siempre" ? "saldrá primero" : "aparecerá con más peso"
                }.`,
          ),
        onError: (e) =>
          notificar(
            "error",
            "No se pudo ajustar",
            e instanceof ErrorApi ? e.message : "Intenta de nuevo.",
          ),
      },
    );
  }

  function aplicarPreajuste(preajuste: (typeof PREAJUSTES)[number]) {
    guardarPesos.mutate(preajuste.pesos, {
      onSuccess: () =>
        notificar(
          "exito",
          `Modo «${preajuste.titulo}» activado`,
          preajuste.consecuencia,
        ),
      onError: () => notificar("error", "No se pudo cambiar el modo"),
    });
  }

  function pedirAnalisis() {
    analizar.mutate(tiendaId, {
      onSuccess: (datos) =>
        notificar(
          "exito",
          datos.desde_cache ? "Nada había cambiado" : "Análisis actualizado",
          datos.desde_cache
            ? "Se recuperó el análisis anterior sin volver a consultar al modelo."
            : `${datos.modelo} revisó el catálogo, las ventas y las relaciones de ${tienda?.nombre ?? "la plaza"}.`,
        ),
      onError: (e) =>
        notificar(
          "error",
          "No se pudo analizar",
          e instanceof ErrorApi ? e.message : "Intenta de nuevo.",
        ),
    });
  }

  return (
    <div className="flex flex-col gap-3">
      <section className="tarjeta p-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <h1 className="text-base font-semibold">
              Qué sugiere el sistema, y por qué
            </h1>
            <p className="mt-1 max-w-3xl text-sm text-acero">
              Aquí ves cada sugerencia que el mostrador puede hacer y puedes
              cambiarla. Los cambios se aplican de inmediato.
            </p>
          </div>
          <button
            onClick={() => setAyuda((v) => !v)}
            className="boton boton-suave flex shrink-0 items-center gap-1.5 px-2.5 py-1.5 text-xs"
            aria-expanded={ayuda}
          >
            <HelpCircle size={14} aria-hidden />
            Cómo funciona
            <ChevronDown
              size={13}
              style={{ transform: ayuda ? "rotate(180deg)" : "none" }}
              className="transition-transform"
              aria-hidden
            />
          </button>
        </div>

        {ayuda && (
          <div className="aparece mt-3 grid gap-2 border-t border-linea pt-3 sm:grid-cols-3">
            <div>
              <p className="text-xs font-semibold" style={{ color: "#1d4ed8" }}>
                Lo dicen las ventas
              </p>
              <p className="mt-0.5 text-xs leading-snug text-acero">
                Dos productos que los clientes ya se llevaron juntos. Cuantas más
                veces pasó, más fuerte es la sugerencia.
              </p>
            </div>
            <div>
              <p className="text-xs font-semibold" style={{ color: "#0f766e" }}>
                Va con el producto
              </p>
              <p className="mt-0.5 text-xs leading-snug text-acero">
                Piezas del mismo trabajo aunque nunca se hayan vendido juntas: un
                soplete necesita gas, un tubo necesita pegamento.
              </p>
            </div>
            <div>
              <p className="text-xs font-semibold" style={{ color: "#6d28d9" }}>
                «En lugar de» vs «además de»
              </p>
              <p className="mt-0.5 text-xs leading-snug text-acero">
                <strong>En lugar de</strong> es un cambio de material más
                adecuado a la sucursal. <strong>Además de</strong> es algo que se
                suma al ticket.
              </p>
            </div>
          </div>
        )}
      </section>

      {/* El analista va antes de los modos: primero se lee que esta
          pasando, despues se decide cuanta evidencia exigir. */}
      <PanelAnalisis
        nombreTienda={tienda?.nombre ?? ""}
        datos={analisis}
        cargando={cargandoAnalisis}
        analizando={analizar.isPending}
        onAnalizar={pedirAnalisis}
      />

      <section className="tarjeta p-4">
        <h2 className="text-sm font-semibold">¿En qué se fija más el sistema?</h2>
        <p className="mt-0.5 text-xs text-acero">
          Cambia el equilibrio entre lo ya vendido y el tipo de producto.
        </p>

        <div className="mt-3 grid gap-2 sm:grid-cols-3">
          {PREAJUSTES.map((preajuste) => {
            const seleccionado = activo === preajuste.id;
            return (
              <button
                key={preajuste.id}
                onClick={() => aplicarPreajuste(preajuste)}
                disabled={guardarPesos.isPending}
                aria-pressed={seleccionado}
                className="tarjeta tarjeta-activa p-3 text-left"
                style={{
                  borderColor: seleccionado
                    ? "var(--color-acento)"
                    : "var(--color-linea)",
                  borderWidth: seleccionado ? 2 : 1,
                  background: seleccionado
                    ? "color-mix(in srgb, var(--color-acento) 6%, #fff)"
                    : "#fff",
                }}
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="text-sm font-medium">{preajuste.titulo}</span>
                  {seleccionado && (
                    <span
                      className="shrink-0 rounded-full px-1.5 py-0.5 text-[10px] font-medium"
                      style={{
                        background: "var(--color-acento)",
                        color: "#fff",
                      }}
                    >
                      activo
                    </span>
                  )}
                </div>
                <p className="mt-1 text-xs leading-snug text-acero">
                  {preajuste.texto}
                </p>
                <p className="mt-1 text-[11px] leading-snug text-acero opacity-80">
                  {preajuste.consecuencia}
                </p>
                {/* El efecto medido, no la intencion: es lo que separa un modo
                    que hace algo de un texto bonito. */}
                <p
                  className="cifra mt-1.5 border-t border-linea pt-1.5 text-[10px]"
                  style={{ color: "var(--color-acento)" }}
                >
                  {preajuste.efecto}
                </p>
              </button>
            );
          })}
        </div>

        <button
          onClick={() => setTecnico((v) => !v)}
          className="mt-2 text-[11px] text-acero underline underline-offset-2 hover:text-tinta"
          aria-expanded={tecnico}
        >
          {tecnico ? "Ocultar" : "Ver"} valores exactos
        </button>
        {tecnico && (
          <p className="cifra aparece mt-1 text-[11px] text-acero">
            {Object.entries(pesos)
              .map(([k, v]) => `${k}=${v}`)
              .join("  ·  ")}
            {activo === null && "  (ajuste personalizado)"}
          </p>
        )}
      </section>

      <div className="flex flex-wrap items-center gap-2">
        <div className="tarjeta flex items-center gap-2 px-2.5 py-1.5">
          <Search size={14} className="shrink-0 text-acero" aria-hidden />
          <input
            value={busqueda}
            onChange={(e) => setBusqueda(e.target.value)}
            placeholder="Buscar producto…"
            aria-label="Buscar relaciones"
            className="w-52 min-w-0 bg-transparent outline-none placeholder:text-acero"
          />
        </div>
        <select
          value={tipo}
          onChange={(e) => setTipo(e.target.value)}
          aria-label="Tipo de sugerencia"
          className="tarjeta cursor-pointer px-2.5 py-1.5 outline-none"
        >
          <option value="">Todas las sugerencias</option>
          <option value="complemento">Solo «además de»</option>
          <option value="sustituto">Solo «en lugar de»</option>
        </select>
        <select
          value={fuente}
          onChange={(e) => setFuente(e.target.value)}
          aria-label="Origen de la sugerencia"
          className="tarjeta cursor-pointer px-2.5 py-1.5 outline-none"
        >
          <option value="">Cualquier origen</option>
          <option value="historico">Lo dicen las ventas</option>
          <option value="atributos">Va con el producto</option>
        </select>

        <p className="ml-auto text-xs text-acero">
          <span className="cifra font-medium text-tinta">{relaciones.length}</span>{" "}
          sugerencias ·{" "}
          <span className="cifra">{desdeVentas}</span> con ventas detrás
          {ocultas > 0 && (
            <>
              {" · "}
              <span className="cifra" style={{ color: "var(--color-alerta)" }}>
                {ocultas}
              </span>{" "}
              ocultas
            </>
          )}
          {fijadas > 0 && (
            <>
              {" · "}
              <span className="cifra" style={{ color: "var(--color-acento)" }}>
                {fijadas}
              </span>{" "}
              fijadas
            </>
          )}
        </p>
      </div>

      <div className="tarjeta overflow-hidden">
        {isLoading ? (
          <p className="p-4 text-sm text-acero">Cargando sugerencias…</p>
        ) : (
          <TablaRelaciones
            relaciones={filtradas}
            catalogo={catalogo}
            onAjustar={aplicarAjuste}
            ajustando={ajustar.isPending}
          />
        )}
      </div>
    </div>
  );
}
