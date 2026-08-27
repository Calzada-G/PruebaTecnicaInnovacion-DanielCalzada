"use client";

/**
 * El analisis del sistema escrito por el modelo. Componente de presentacion.
 *
 * El boton se apaga solo cuando no hay nada nuevo que analizar. No es un
 * detalle de interfaz: cada pulsacion que no aporta informacion nueva es cuota
 * gastada en volver a preguntar lo mismo. El servidor lo garantiza igual -si
 * la huella coincide devuelve lo guardado sin llamar-, pero el boton apagado
 * lo explica antes de que alguien lo intente.
 */

import {
  AlertTriangle,
  Brain,
  Check,
  ChevronRight,
  RefreshCw,
  Store,
  TrendingUp,
} from "lucide-react";
import type { Analisis, PuntoAnalisis } from "../lib/api";

type Props = {
  nombreTienda: string;
  datos:
    | {
        disponible: boolean;
        hay_analisis: boolean;
        vigente: boolean;
        desde_cache: boolean;
        analisis: Analisis | null;
        modelo: string | null;
        generado_en: string | null;
      }
    | undefined;
  cargando: boolean;
  analizando: boolean;
  onAnalizar: () => void;
};

const IMPACTO = {
  alto: "var(--color-error)",
  medio: "var(--color-alerta)",
  bajo: "var(--color-acero)",
} as const;

function Punto({ punto }: { punto: PuntoAnalisis }) {
  return (
    <li className="rounded-[var(--radio)] border border-linea p-2.5">
      <div className="flex items-start justify-between gap-2">
        <span className="text-xs font-semibold leading-snug">{punto.titulo}</span>
        <span
          className="shrink-0 rounded-full px-1.5 py-0.5 text-[10px] font-medium"
          style={{
            background: `color-mix(in srgb, ${IMPACTO[punto.impacto]} 12%, #fff)`,
            color: IMPACTO[punto.impacto],
          }}
        >
          {punto.impacto}
        </span>
      </div>
      <p className="mt-1 text-[11px] leading-snug text-acero">{punto.analisis}</p>
      {punto.dato && (
        <p className="cifra mt-1 text-[10px] text-acero opacity-80">{punto.dato}</p>
      )}
      {punto.skus.length > 0 && (
        <div className="mt-1.5 flex flex-wrap gap-1">
          {punto.skus.map((sku) => (
            <span
              key={sku}
              className="cifra rounded bg-papel px-1 py-px text-[10px] text-acero"
            >
              {sku}
            </span>
          ))}
        </div>
      )}
    </li>
  );
}

function Columna({
  titulo,
  icono: Icono,
  puntos,
}: {
  titulo: string;
  icono: typeof Store;
  puntos: PuntoAnalisis[];
}) {
  if (puntos.length === 0) return null;
  return (
    <div className="min-w-0">
      <h3 className="mb-1.5 flex items-center gap-1.5 text-xs font-semibold text-acero">
        <Icono size={13} aria-hidden />
        {titulo}
      </h3>
      <ul className="flex flex-col gap-1.5">
        {puntos.map((punto) => (
          <Punto key={punto.titulo} punto={punto} />
        ))}
      </ul>
    </div>
  );
}

export function PanelAnalisis({
  nombreTienda,
  datos,
  cargando,
  analizando,
  onAnalizar,
}: Props) {
  const disponible = datos?.disponible ?? false;
  const vigente = datos?.vigente ?? false;
  const analisis = datos?.analisis ?? null;

  const etiquetaBoton = analizando
    ? "Analizando…"
    : !disponible
      ? "Necesita clave de IA"
      : vigente
        ? "Sin cambios que analizar"
        : analisis
          ? "Volver a analizar"
          : "Analizar el sistema";

  return (
    <section className="tarjeta p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h2 className="flex items-center gap-1.5 text-sm font-semibold">
            <Brain size={15} style={{ color: "var(--color-acento)" }} aria-hidden />
            Análisis del sistema
          </h2>
          <p className="mt-1 max-w-2xl text-xs leading-snug text-acero">
            Una sola consulta al modelo con todo lo que hay en{" "}
            {nombreTienda || "esta plaza"}: catálogo, existencias, ventas y las
            relaciones que ves abajo. No propone qué vender junto —de eso ya se
            encarga el motor— sino qué significan los números.
          </p>
        </div>

        <button
          onClick={onAnalizar}
          disabled={!disponible || vigente || analizando || cargando}
          className="boton boton-primario flex shrink-0 items-center gap-1.5 px-3 py-2 text-sm"
        >
          <RefreshCw
            size={14}
            aria-hidden
            className={analizando ? "animate-spin" : undefined}
          />
          {etiquetaBoton}
        </button>
      </div>

      {!disponible && (
        <p className="mt-3 flex items-start gap-1.5 rounded-[var(--radio)] px-2.5 py-2 text-xs"
           style={{ background: "#fffbeb", color: "var(--color-alerta)" }}>
          <AlertTriangle size={14} className="mt-px shrink-0" aria-hidden />
          Falta <span className="cifra">GEMINI_API_KEY</span> en{" "}
          <span className="cifra">backend/.env</span>. Todo lo demás del sistema
          funciona igual: esto es lo único que la necesita.
        </p>
      )}

      {disponible && vigente && (
        <p
          className="mt-3 flex items-center gap-1.5 text-[11px]"
          style={{ color: "var(--color-exito)" }}
        >
          <Check size={13} aria-hidden />
          Nada ha cambiado en el catálogo, las ventas ni las relaciones desde
          este análisis. Volver a preguntar daría lo mismo y gastaría cuota.
        </p>
      )}

      {analisis && (
        <div className="aparece mt-3 flex flex-col gap-3">
          <p className="rounded-[var(--radio)] border-l-2 py-1 pl-2.5 text-sm leading-snug"
             style={{ borderColor: "var(--color-acento)" }}>
            {analisis.resumen}
          </p>

          <div className="grid gap-3 lg:grid-cols-2">
            <Columna titulo="El negocio" icono={Store} puntos={analisis.negocio} />
            <Columna titulo="El sistema" icono={TrendingUp} puntos={analisis.sistema} />
          </div>

          {analisis.decisiones.length > 0 && (
            <div>
              <h3 className="mb-1.5 text-xs font-semibold text-acero">
                Qué decidir
              </h3>
              <ul className="flex flex-col gap-1.5">
                {analisis.decisiones.map((decision) => (
                  <li
                    key={decision.titulo}
                    className="flex items-start gap-2 rounded-[var(--radio)] p-2.5"
                    style={{ background: "color-mix(in srgb, var(--color-acento) 6%, #fff)" }}
                  >
                    <ChevronRight
                      size={14}
                      className="mt-px shrink-0"
                      style={{ color: "var(--color-acento)" }}
                      aria-hidden
                    />
                    <div className="min-w-0">
                      <p className="text-xs font-semibold">{decision.titulo}</p>
                      <p className="mt-0.5 text-[11px] leading-snug text-acero">
                        {decision.porque}
                      </p>
                      <p className="mt-0.5 text-[11px] font-medium leading-snug">
                        {decision.accion}
                      </p>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          )}

          <p className="text-[10px] text-acero">
            Escrito por <span className="cifra">{datos?.modelo}</span> el{" "}
            <span className="cifra">{datos?.generado_en}</span>
            {datos?.desde_cache && " · recuperado sin volver a consultar"}. Es
            una opinión de un modelo sobre los datos, no una regla del sistema:
            lo que se recomienda en el mostrador no lo decide esto.
          </p>
        </div>
      )}
    </section>
  );
}
