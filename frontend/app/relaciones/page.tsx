"use client";

import { useState } from "react";
import { TablaRelaciones } from "../../componentes/TablaRelaciones";
import {
  useAjustarRelacion,
  usePesos,
  useRelaciones,
} from "../../hooks/useRecomendaciones";

export default function Relaciones() {
  const [tipo, setTipo] = useState("");
  const [fuente, setFuente] = useState("");
  const [busqueda, setBusqueda] = useState("");

  const { data: relaciones = [], isLoading } = useRelaciones(
    tipo || undefined,
    fuente || undefined,
  );
  const { data: pesos = {} } = usePesos();
  const { ajustar, guardarPesos } = useAjustarRelacion();

  const filtradas = busqueda
    ? relaciones.filter((r) =>
        `${r.sku_origen} ${r.sku_destino} ${r.nombre_origen} ${r.nombre_destino}`
          .toLowerCase()
          .includes(busqueda.toLowerCase()),
      )
    : relaciones;

  const bloqueadas = relaciones.filter((r) => r.estado === "bloqueada").length;
  const fijadas = relaciones.filter((r) => r.estado === "fijada").length;

  return (
    <div className="flex flex-col gap-3">
      <section className="border border-linea bg-white p-3">
        <h2 className="mb-1 text-xs font-semibold uppercase tracking-wide text-acero">
          Peso de cada fuente
        </h2>
        <p className="mb-2 text-xs text-acero">
          Cuanto pesa cada fuente al ordenar. Subir el historico hace al sistema
          mas conservador (solo propone lo ya visto); subir los atributos lo hace
          cubrir mas catalogo, incluido lo que nunca se ha vendido.
        </p>
        <div className="flex flex-wrap items-end gap-3">
          {Object.entries(pesos).map(([nombre, valor]) => (
            <label key={nombre} className="flex flex-col gap-1 text-xs text-acero">
              {nombre}
              <input
                type="number"
                min={0}
                step="0.1"
                defaultValue={valor}
                aria-label={`Peso de ${nombre}`}
                onBlur={(e) => {
                  const nuevo = Number(e.target.value);
                  if (Number.isFinite(nuevo) && nuevo !== valor) {
                    guardarPesos.mutate({ ...pesos, [nombre]: nuevo });
                  }
                }}
                className="cifra w-24 border border-linea px-2 py-1 text-tinta"
              />
            </label>
          ))}
          {guardarPesos.isPending && (
            <span className="text-xs text-acero">guardando...</span>
          )}
        </div>
      </section>

      <div className="flex flex-wrap items-center gap-2">
        <input
          value={busqueda}
          onChange={(e) => setBusqueda(e.target.value)}
          placeholder="Filtrar por SKU o nombre"
          aria-label="Filtrar relaciones"
          className="w-64 border border-linea bg-white px-2 py-1 outline-none"
        />
        <select
          value={tipo}
          onChange={(e) => setTipo(e.target.value)}
          aria-label="Tipo de relacion"
          className="border border-linea bg-white px-2 py-1"
        >
          <option value="">Todos los tipos</option>
          <option value="complemento">Complementos</option>
          <option value="sustituto">Sustitutos</option>
        </select>
        <select
          value={fuente}
          onChange={(e) => setFuente(e.target.value)}
          aria-label="Fuente"
          className="border border-linea bg-white px-2 py-1"
        >
          <option value="">Todas las fuentes</option>
          <option value="historico">Historico</option>
          <option value="atributos">Atributos</option>
        </select>
        <span className="cifra text-xs text-acero">
          {filtradas.length} relaciones · {bloqueadas} bloqueadas · {fijadas} fijadas
        </span>
      </div>

      <div className="overflow-x-auto border border-linea bg-white">
        {isLoading ? (
          <p className="p-3 text-acero">Cargando relaciones...</p>
        ) : (
          <TablaRelaciones
            relaciones={filtradas}
            onEstado={(id, estado) => ajustar.mutate({ id, cambios: { estado } })}
            onPeso={(id, peso_manual) =>
              ajustar.mutate({ id, cambios: { peso_manual } })
            }
            ajustando={ajustar.isPending}
          />
        )}
      </div>

      <p className="text-xs text-acero">
        Bloquear una relacion la saca del mostrador de inmediato, sin reiniciar
        nada. Los ajustes sobreviven a reconstruir las reglas con
        <span className="cifra"> construir_relaciones.py</span>.
      </p>
    </div>
  );
}
