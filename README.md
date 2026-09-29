# Contactos · grupos de conexión

App para registrar personas, llamarlas por teléfono y sumarlas a un grupo de conexión.
FastAPI + SQLite + una página web sin build step.

## Correr

```bash
python -m venv .venv && source .venv/bin/activate   # en Windows: .venv\Scripts\activate
pip install -r requirements.txt
python seed.py            # opcional: dos grupos y tres contactos de ejemplo
uvicorn app.main:app --reload
```

- App: http://127.0.0.1:8000
- Docs interactivas de la API: http://127.0.0.1:8000/docs

La base se crea sola en `contactos.db` la primera vez.

## Modelo de datos

Tres tablas (`schema.sql` tiene el DDL completo):

| Tabla | Para qué |
|---|---|
| `grupos` | Los grupos disponibles: día, horario, anfitrión, cupo máximo. |
| `contactos` | La persona: nombre, teléfono único, horario preferido, estado y a qué grupo pertenece. |
| `llamadas` | Un registro por intento de llamada, con resultado y comentario. |

La separación importa: `contactos.estado` es el resumen ("interesado"), y `llamadas` es la
evidencia de cuántas veces se lo intentó y qué se habló. Sin esa tabla, después no sabés si
alguien "no atendió" una vez o cinco.

Estados de un contacto:

```
pendiente → sin_respuesta → interesado → sumado
                         ↘ no_interesado
```

El estado no se edita a mano desde la app: se deriva del resultado de la última llamada
(`POST /api/contactos/{id}/llamadas`). Así el estado nunca miente sobre lo que pasó.

## Endpoints

| Método | Ruta | Qué hace |
|---|---|---|
| POST | `/api/contactos` | Alta. Rechaza teléfonos duplicados (409). |
| GET | `/api/contactos` | Lista, con filtros `estado`, `grupo_id`, `buscar`. |
| GET | `/api/contactos/cola` | A quién llamar: pendientes y sin respuesta, más viejos primero. |
| PATCH | `/api/contactos/{id}` | Edición parcial. |
| DELETE | `/api/contactos/{id}` | Baja. |
| POST | `/api/contactos/{id}/llamadas` | Registra el intento y mueve el estado. Valida cupo del grupo. |
| GET/POST | `/api/grupos` | Grupos y su cupo disponible. |
| GET | `/api/metricas` | Totales y tasa de conversión. |
| GET | `/api/contactos.csv` | Exporta todo a CSV. |

## Reglas de negocio ya implementadas

- Teléfono único y validado por formato.
- No se puede sumar a alguien a un grupo sin cupo (409).
- `autoriza_contacto` queda registrado; la cola puede filtrar solo a los que autorizaron
  (`?solo_autorizados=true`).
- Borrar un contacto borra sus llamadas; borrar un grupo deja a sus contactos sin grupo.

## Contraseña compartida

Toda la app —la interfaz y la API— queda detrás de una sola contraseña para todo el equipo,
con el cuadro de usuario/contraseña nativo del navegador (no hay pantalla de login que mantener).
El usuario que escribas no importa, ninguno se guarda; solo se valida la contraseña.

**En Railway**: *Variables* → agregá `APP_PASSWORD` con el valor que quieras. Se aplica al
redesplegar (Railway lo hace solo apenas guardás la variable).

**En local**: copiá `.env.example` a `.env` y completá `APP_PASSWORD`, o exportala antes de
levantar el servidor:

```bash
export APP_PASSWORD="la-contraseña-del-equipo"
uvicorn app.main:app --reload
```

Si no está definida, la app queda sin contraseña — pensado para probar en tu máquina, nunca
para lo que subas a Railway.

Para cambiarla más adelante, simplemente editás el valor de la variable en Railway; no hace
falta tocar código. Como es HTTP Basic, no hay "cerrar sesión": el navegador guarda la
contraseña hasta que cerrás la pestaña o la borrás vos mismo desde la configuración del navegador.

## Desplegar en Railway

La app ya está lista para esto: `Procfile` y `railway.json` le dicen a Railway cómo
arrancarla, y `app/database.py` detecta sola la base de Postgres que Railway inyecta.

**Opción A — desde GitHub (recomendada para un equipo):**

1. Subí esta carpeta a un repositorio de GitHub.
2. En [railway.app](https://railway.app) → *New Project* → *Deploy from GitHub repo* → elegí el repo.
3. En el mismo proyecto: *New* → *Database* → *Add PostgreSQL*. Railway crea la variable
   `DATABASE_URL` y se la comparte automáticamente al servicio web — no hay que copiarla a mano.
4. Railway detecta el `Procfile` y lo despliega solo. Cuando termine, te da una URL pública
   (`Settings` → `Networking` → `Generate Domain`).
5. Compartí esa URL con tu equipo. Cada uno entra directo desde el navegador, sin instalar nada.

**Opción B — desde la terminal:**

```bash
npm install -g @railway/cli    # o: curl -fsSL https://railway.app/install.sh | sh
railway login
railway init
railway add                    # elegí PostgreSQL
railway up
railway domain                 # genera la URL pública
```

**Cargar los datos de ejemplo en la nube** (opcional, una sola vez):

```bash
railway run python seed.py
```

**Variables de entorno**: no hace falta configurar nada a mano. Railway define `DATABASE_URL`
y `PORT` solo; el código las lee con `os.getenv`.

## Pasar a PostgreSQL en forma local (sin Railway)

```bash
pip install "psycopg[binary]"
export DATABASE_URL="postgresql+psycopg://usuario:clave@localhost/contactos"
```

`schema.sql` tiene al final las equivalencias de tipos si preferís crear las tablas a mano.

## Lo que le falta para producción

- Migraciones con Alembic en vez de `create_all` (para cambiar el esquema sin perder datos).
- Tests automáticos.
- HTTPS ya lo da Railway solo; no hace falta configurar certificados.
- La contraseña es única para todo el equipo: no distingue quién hizo qué. Si más adelante
  necesitás saber qué usuario cargó o llamó a cada contacto, hace falta login individual.
