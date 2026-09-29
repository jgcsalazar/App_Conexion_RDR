"""Conexión a la base.

Local: SQLite en un archivo (no necesita configuración).
Producción (Railway): toma la variable DATABASE_URL que Railway inyecta sola
al conectar un servicio de PostgreSQL. Railway la entrega como
"postgres://..."; SQLAlchemy con el driver psycopg necesita el prefijo
"postgresql+psycopg://...", así que la convertimos acá, en un solo lugar.
"""

import os

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./contactos.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, pool_pre_ping=True, connect_args=connect_args)

# SQLite ignora las foreign keys salvo que se activen en cada conexión.
if DATABASE_URL.startswith("sqlite"):

    @event.listens_for(engine, "connect")
    def _activar_foreign_keys(dbapi_connection, _):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    """Dependencia de FastAPI: abre una sesión por request y la cierra siempre."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
