"""Modelos de datos (SQLAlchemy 2.0). Equivalen 1 a 1 con schema.sql."""

from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class Origen(str, Enum):
    evento = "evento"
    referido = "referido"
    redes = "redes"
    web = "web"
    otro = "otro"


class Horario(str, Enum):
    manana = "manana"
    tarde = "tarde"
    noche = "noche"
    sin_preferencia = "sin_preferencia"


class Estado(str, Enum):
    pendiente = "pendiente"
    sin_respuesta = "sin_respuesta"
    interesado = "interesado"
    sumado = "sumado"
    no_interesado = "no_interesado"


class Resultado(str, Enum):
    sin_respuesta = "sin_respuesta"
    interesado = "interesado"
    sumado = "sumado"
    no_interesado = "no_interesado"
    reprogramar = "reprogramar"


class Grupo(Base):
    __tablename__ = "grupos"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120), unique=True)
    zona: Mapped[str | None] = mapped_column(String(120))
    dia_semana: Mapped[str | None] = mapped_column(String(20))
    horario: Mapped[str | None] = mapped_column(String(20))
    anfitrion: Mapped[str | None] = mapped_column(String(120))
    cupo_maximo: Mapped[int] = mapped_column(Integer, default=12)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    contactos: Mapped[list["Contacto"]] = relationship(back_populates="grupo")

    @property
    def cupo_disponible(self) -> int:
        ocupados = sum(1 for c in self.contactos if c.estado == Estado.sumado)
        return max(self.cupo_maximo - ocupados, 0)


class Contacto(Base):
    __tablename__ = "contactos"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120))
    telefono: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    email: Mapped[str | None] = mapped_column(String(120))
    zona: Mapped[str | None] = mapped_column(String(120))
    origen: Mapped[Origen] = mapped_column(default=Origen.otro)
    horario_preferido: Mapped[Horario] = mapped_column(default=Horario.sin_preferencia)
    estado: Mapped[Estado] = mapped_column(default=Estado.pendiente, index=True)
    autoriza_contacto: Mapped[bool] = mapped_column(Boolean, default=False)
    notas: Mapped[str | None] = mapped_column(Text)
    grupo_id: Mapped[int | None] = mapped_column(ForeignKey("grupos.id", ondelete="SET NULL"))
    creado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    grupo: Mapped[Grupo | None] = relationship(back_populates="contactos")
    llamadas: Mapped[list["Llamada"]] = relationship(
        back_populates="contacto",
        cascade="all, delete-orphan",
        order_by="Llamada.fecha.desc()",
    )


class Llamada(Base):
    __tablename__ = "llamadas"

    id: Mapped[int] = mapped_column(primary_key=True)
    contacto_id: Mapped[int] = mapped_column(
        ForeignKey("contactos.id", ondelete="CASCADE"), index=True
    )
    fecha: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    resultado: Mapped[Resultado] = mapped_column()
    comentario: Mapped[str | None] = mapped_column(Text)
    llamado_por: Mapped[str | None] = mapped_column(String(120))

    contacto: Mapped[Contacto] = relationship(back_populates="llamadas")
