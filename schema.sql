-- Esquema de la base de contactos para grupos de conexión.
-- Dialecto: SQLite. Al final del archivo hay notas para migrar a PostgreSQL.
-- La app crea estas tablas sola al arrancar (SQLAlchemy), este archivo es la
-- referencia del modelo y sirve para crear la base a mano: sqlite3 contactos.db < schema.sql

PRAGMA foreign_keys = ON;

-- Grupos de conexión disponibles (día, horario, anfitrión, cupo).
CREATE TABLE IF NOT EXISTS grupos (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre        TEXT    NOT NULL UNIQUE,
    zona          TEXT,
    dia_semana    TEXT,               -- 'martes', 'jueves', ...
    horario       TEXT,               -- '20:00'
    anfitrion     TEXT,
    cupo_maximo   INTEGER NOT NULL DEFAULT 12,
    activo        INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0, 1)),
    creado_en     TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- Personas a contactar. El teléfono es único: evita cargar dos veces al mismo.
CREATE TABLE IF NOT EXISTS contactos (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre         TEXT    NOT NULL,
    telefono       TEXT    NOT NULL UNIQUE,
    email          TEXT,
    zona           TEXT,
    origen         TEXT    NOT NULL DEFAULT 'otro'
                   CHECK (origen IN ('evento', 'referido', 'redes', 'web', 'otro')),
    horario_preferido TEXT NOT NULL DEFAULT 'sin_preferencia'
                   CHECK (horario_preferido IN ('manana', 'tarde', 'noche', 'sin_preferencia')),
    estado         TEXT    NOT NULL DEFAULT 'pendiente'
                   CHECK (estado IN ('pendiente', 'sin_respuesta', 'interesado', 'sumado', 'no_interesado')),
    autoriza_contacto INTEGER NOT NULL DEFAULT 0 CHECK (autoriza_contacto IN (0, 1)),
    notas          TEXT,
    grupo_id       INTEGER REFERENCES grupos(id) ON DELETE SET NULL,
    creado_en      TEXT    NOT NULL DEFAULT (datetime('now')),
    actualizado_en TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- Historial de llamadas: una fila por intento. El estado del contacto es el
-- resumen; esta tabla es la evidencia de cuántas veces se lo intentó y cuándo.
CREATE TABLE IF NOT EXISTS llamadas (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    contacto_id  INTEGER NOT NULL REFERENCES contactos(id) ON DELETE CASCADE,
    fecha        TEXT    NOT NULL DEFAULT (datetime('now')),
    resultado    TEXT    NOT NULL
                 CHECK (resultado IN ('sin_respuesta', 'interesado', 'sumado', 'no_interesado', 'reprogramar')),
    comentario   TEXT,
    llamado_por  TEXT
);

CREATE INDEX IF NOT EXISTS ix_contactos_estado   ON contactos(estado);
CREATE INDEX IF NOT EXISTS ix_contactos_grupo    ON contactos(grupo_id);
CREATE INDEX IF NOT EXISTS ix_llamadas_contacto  ON llamadas(contacto_id);

-- Vista práctica: a quién llamar primero (pendientes y los que quedaron sin respuesta),
-- ordenados por antigüedad de carga.
CREATE VIEW IF NOT EXISTS v_cola_de_llamados AS
SELECT c.id, c.nombre, c.telefono, c.horario_preferido, c.estado,
       (SELECT COUNT(*) FROM llamadas l WHERE l.contacto_id = c.id) AS intentos,
       (SELECT MAX(l.fecha) FROM llamadas l WHERE l.contacto_id = c.id) AS ultimo_intento
FROM contactos c
WHERE c.estado IN ('pendiente', 'sin_respuesta')
ORDER BY c.creado_en;

-- Notas para PostgreSQL:
--   INTEGER PRIMARY KEY AUTOINCREMENT  ->  GENERATED ALWAYS AS IDENTITY
--   TEXT ... CHECK (x IN (...))        ->  CREATE TYPE ... AS ENUM (...)
--   INTEGER 0/1                        ->  BOOLEAN
--   TEXT DEFAULT (datetime('now'))     ->  TIMESTAMPTZ DEFAULT now()
-- El código de la app no cambia: solo la URL en DATABASE_URL.
