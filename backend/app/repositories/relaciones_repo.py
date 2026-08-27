"""SQL de la tabla `relaciones` y de los pesos por fuente.

`relaciones` es a la vez el catalogo auditable de lo que el sistema encontro y
la superficie de control del negocio: lo que se bloquea o se fija aqui cambia
el mostrador sin reiniciar nada.
"""

import sqlite3

CAMPOS = (
    "id, sku_origen, sku_destino, tipo, fuente, score, soporte, confianza, "
    "lift, justificacion, justificacion_ia, estado, peso_manual"
)


def reemplazar(bd: sqlite3.Connection, relaciones: list[dict]) -> None:
    """Inserta o refresca relaciones SIN pisar los ajustes del negocio.

    `estado` y `peso_manual` los pone una persona; reconstruir las reglas no
    puede deshacer esa decision o el panel seria papel mojado.

    `justificacion_ia` si se limpia, pero solo cuando el texto de plantilla
    cambio: significa que los numeros que el LLM redacto ya no son ciertos.
    """
    bd.executemany(
        """INSERT INTO relaciones
           (sku_origen, sku_destino, tipo, fuente, score, soporte, confianza,
            lift, justificacion)
           VALUES (:sku_origen, :sku_destino, :tipo, :fuente, :score, :soporte,
                   :confianza, :lift, :justificacion)
           ON CONFLICT (sku_origen, sku_destino, tipo) DO UPDATE SET
               fuente        = excluded.fuente,
               score         = excluded.score,
               soporte       = excluded.soporte,
               confianza     = excluded.confianza,
               lift          = excluded.lift,
               justificacion_ia = CASE
                   WHEN relaciones.justificacion <> excluded.justificacion
                   THEN NULL ELSE relaciones.justificacion_ia END,
               justificacion = excluded.justificacion""",
        relaciones,
    )


def eliminar_huerfanas(bd: sqlite3.Connection, vigentes: list[tuple]) -> int:
    """Borra reglas que ya no se derivan de los datos, salvo las tocadas a mano.

    Una relacion que el negocio bloqueo o fijo se conserva aunque el algoritmo
    deje de proponerla: si se borrara, volveria a aparecer en la siguiente
    reconstruccion como si nunca la hubieran bloqueado.
    """
    actuales = {
        (f["sku_origen"], f["sku_destino"], f["tipo"])
        for f in bd.execute(
            "SELECT sku_origen, sku_destino, tipo FROM relaciones WHERE estado = 'activa'"
        )
    }
    sobrantes = actuales - set(vigentes)
    bd.executemany(
        """DELETE FROM relaciones
            WHERE sku_origen = ? AND sku_destino = ? AND tipo = ?
              AND estado = 'activa'""",
        list(sobrantes),
    )
    return len(sobrantes)


def listar(
    bd: sqlite3.Connection,
    tipo: str | None = None,
    fuente: str | None = None,
    id_relacion: int | None = None,
) -> list[sqlite3.Row]:
    """Relaciones con el nombre y la existencia del producto destino.

    Filtrar por `id_relacion` devuelve una sola fila con EXACTAMENTE la misma
    forma que el listado. Asi el PATCH responde la misma representacion que el
    GET sin duplicar el JOIN en otra consulta.
    """
    condiciones, parametros = [], []
    if tipo:
        condiciones.append("r.tipo = ?")
        parametros.append(tipo)
    if fuente:
        condiciones.append("r.fuente = ?")
        parametros.append(fuente)
    if id_relacion is not None:
        condiciones.append("r.id = ?")
        parametros.append(id_relacion)
    where = f"WHERE {' AND '.join(condiciones)}" if condiciones else ""
    return bd.execute(
        f"""SELECT {CAMPOS.replace('id,', 'r.id,')},
                   po.nombre AS nombre_origen, pd.nombre AS nombre_destino,
                   pd.stock  AS stock_destino, pd.activo AS activo_destino
              FROM relaciones r
              JOIN productos po ON po.sku = r.sku_origen
              JOIN productos pd ON pd.sku = r.sku_destino
              {where}
             ORDER BY r.estado = 'bloqueada', r.score DESC, r.sku_origen""",
        parametros,
    ).fetchall()


def obtener(bd: sqlite3.Connection, id_relacion: int) -> sqlite3.Row | None:
    return bd.execute(
        f"SELECT {CAMPOS} FROM relaciones WHERE id = ?", (id_relacion,)
    ).fetchone()


def actualizar(bd: sqlite3.Connection, id_relacion: int, cambios: dict) -> int:
    asignaciones = ", ".join(f"{campo} = :{campo}" for campo in cambios)
    cur = bd.execute(
        f"UPDATE relaciones SET {asignaciones} WHERE id = :id",
        {**cambios, "id": id_relacion},
    )
    return cur.rowcount


def ajustes(bd: sqlite3.Connection) -> dict[tuple[str, str, str], dict]:
    """Estado y peso manual por relacion, para aplicarlos a cualquier fuente."""
    return {
        (f["sku_origen"], f["sku_destino"], f["tipo"]): {
            "estado": f["estado"],
            "peso_manual": f["peso_manual"],
        }
        for f in bd.execute(
            "SELECT sku_origen, sku_destino, tipo, estado, peso_manual FROM relaciones"
        )
    }


def pesos(bd: sqlite3.Connection) -> dict[str, float]:
    return {
        f["fuente"]: f["peso"]
        for f in bd.execute("SELECT fuente, peso FROM config_pesos")
    }


def guardar_pesos(bd: sqlite3.Connection, nuevos: dict[str, float]) -> None:
    bd.executemany(
        """INSERT INTO config_pesos (fuente, peso) VALUES (?, ?)
           ON CONFLICT (fuente) DO UPDATE SET peso = excluded.peso""",
        list(nuevos.items()),
    )


def guardar_justificacion_ia(
    bd: sqlite3.Connection, id_relacion: int, texto: str | None
) -> None:
    bd.execute(
        "UPDATE relaciones SET justificacion_ia = ? WHERE id = ?",
        (texto, id_relacion),
    )
