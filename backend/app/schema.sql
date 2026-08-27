-- Esquema completo de la POC. seed.py lo ejecuta entero tras borrar la base.

CREATE TABLE tiendas (
    id     TEXT PRIMARY KEY,          -- slug ASCII: cancun, merida, cdmx...
    nombre TEXT NOT NULL,             -- con acentos, solo para mostrar
    perfil TEXT NOT NULL,
    acento TEXT NOT NULL
);

CREATE TABLE productos (
    sku             TEXT PRIMARY KEY,
    nombre          TEXT NOT NULL,
    descripcion     TEXT NOT NULL DEFAULT '',
    categoria       TEXT NOT NULL,
    material        TEXT NOT NULL DEFAULT '',
    uso_recomendado TEXT NOT NULL DEFAULT '',
    precio          REAL NOT NULL CHECK (precio >= 0),
    -- Ultima defensa: aunque alguien escriba un UPDATE mal, la base no acepta
    -- inventario negativo. La primera defensa es el WHERE de compra_service.
    stock           INTEGER NOT NULL CHECK (stock >= 0),
    activo          INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0, 1)),
    creado_en       TEXT NOT NULL DEFAULT (datetime('now')),
    actualizado_en  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_productos_categoria ON productos (categoria);
CREATE INDEX idx_productos_activo ON productos (activo);

CREATE TABLE ventas (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id TEXT NOT NULL,
    sku       TEXT NOT NULL REFERENCES productos (sku),
    cantidad  INTEGER NOT NULL CHECK (cantidad > 0),
    tienda_id TEXT NOT NULL REFERENCES tiendas (id),
    fecha     TEXT NOT NULL
);

CREATE INDEX idx_ventas_ticket ON ventas (ticket_id);
CREATE INDEX idx_ventas_sku ON ventas (sku);
CREATE INDEX idx_ventas_tienda ON ventas (tienda_id);

-- Append-only: nunca se actualiza ni se borra. Es la auditoria de por que el
-- stock vale lo que vale, y permite reconstruirlo sumando deltas.
CREATE TABLE movimientos_inventario (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    sku         TEXT NOT NULL REFERENCES productos (sku),
    delta       INTEGER NOT NULL,
    stock_final INTEGER NOT NULL,
    motivo      TEXT NOT NULL,
    tienda_id   TEXT REFERENCES tiendas (id),
    ticket_id   TEXT,
    creado_en   TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_movimientos_sku ON movimientos_inventario (sku);

-- Idempotencia de compras. La PK es la que hace de candado: dos peticiones con
-- la misma Idempotency-Key no pueden descontar dos veces.
CREATE TABLE operaciones (
    clave     TEXT PRIMARY KEY,
    respuesta TEXT,
    creado_en TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE relaciones (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    sku_origen       TEXT NOT NULL REFERENCES productos (sku),
    sku_destino      TEXT NOT NULL REFERENCES productos (sku),
    tipo             TEXT NOT NULL CHECK (tipo IN ('complemento', 'sustituto')),
    fuente           TEXT NOT NULL,
    score            REAL NOT NULL DEFAULT 0,
    soporte          INTEGER,
    confianza        REAL,
    lift             REAL,
    justificacion    TEXT NOT NULL DEFAULT '',
    -- Redaccion opcional del LLM. Se sirve en lugar de justificacion cuando
    -- existe; separarlas deja revertir y auditar que texto escribio la maquina.
    justificacion_ia TEXT,
    estado           TEXT NOT NULL DEFAULT 'activa'
                     CHECK (estado IN ('activa', 'bloqueada', 'fijada')),
    peso_manual      REAL,
    UNIQUE (sku_origen, sku_destino, tipo)
);

CREATE INDEX idx_relaciones_origen ON relaciones (sku_origen);

CREATE TABLE config_pesos (
    fuente TEXT PRIMARY KEY,
    peso   REAL NOT NULL CHECK (peso >= 0)
);

-- Analisis del sistema escrito por el LLM. Se guarda con la HUELLA del estado
-- que analizo: si el sistema no ha cambiado desde entonces, se devuelve este
-- texto y no se llama al modelo. Es lo que hace que el boton no gaste tokens
-- por curiosidad.
CREATE TABLE analisis_ia (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    tienda_id TEXT NOT NULL REFERENCES tiendas (id),
    huella    TEXT NOT NULL,
    modelo    TEXT NOT NULL,
    contenido TEXT NOT NULL,          -- JSON con el analisis ya validado
    creado_en TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (tienda_id, huella)
);

CREATE INDEX idx_analisis_tienda ON analisis_ia (tienda_id, creado_en DESC);
