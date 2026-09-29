"""Esquemas Pydantic: qué acepta y qué devuelve la API."""

import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from .models import Estado, Horario, Origen, Resultado

TELEFONO_RE = re.compile(r"^\+?[\d\s\-()]{7,25}$")


class GrupoCrear(BaseModel):
    nombre: str = Field(min_length=2, max_length=120)
    zona: str | None = None
    dia_semana: str | None = None
    horario: str | None = None
    anfitrion: str | None = None
    cupo_maximo: int = Field(default=12, ge=1, le=100)
    activo: bool = True


class GrupoActualizar(BaseModel):
    """Todos los campos opcionales: sirve para PATCH parciales."""

    nombre: str | None = Field(default=None, min_length=2, max_length=120)
    zona: str | None = None
    dia_semana: str | None = None
    horario: str | None = None
    anfitrion: str | None = None
    cupo_maximo: int | None = Field(default=None, ge=1, le=100)
    activo: bool | None = None


class GrupoLeer(GrupoCrear):
    model_config = ConfigDict(from_attributes=True)

    id: int
    cupo_disponible: int


class ContactoBase(BaseModel):
    nombre: str = Field(min_length=2, max_length=120)
    telefono: str
    email: EmailStr | None = None
    zona: str | None = None
    origen: Origen = Origen.otro
    horario_preferido: Horario = Horario.sin_preferencia
    autoriza_contacto: bool = False
    notas: str | None = None
    grupo_id: int | None = None

    @field_validator("telefono")
    @classmethod
    def validar_telefono(cls, v: str) -> str:
        v = v.strip()
        if not TELEFONO_RE.match(v):
            raise ValueError("Teléfono inválido. Formato esperado: +54 9 11 5555 1234")
        return v


class ContactoCrear(ContactoBase):
    pass


class ContactoActualizar(BaseModel):
    """Todos los campos opcionales: sirve para PATCH parciales."""

    nombre: str | None = None
    telefono: str | None = None
    email: EmailStr | None = None
    zona: str | None = None
    origen: Origen | None = None
    horario_preferido: Horario | None = None
    estado: Estado | None = None
    autoriza_contacto: bool | None = None
    notas: str | None = None
    grupo_id: int | None = None


class LlamadaCrear(BaseModel):
    resultado: Resultado
    comentario: str | None = None
    llamado_por: str | None = None
    grupo_id: int | None = None  # si el resultado es "sumado", a qué grupo entra


class LlamadaLeer(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    fecha: datetime
    resultado: Resultado
    comentario: str | None
    llamado_por: str | None


class ContactoLeer(ContactoBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    estado: Estado
    creado_en: datetime
    llamadas: list[LlamadaLeer] = []


class AsignarGrupo(BaseModel):
    grupo_id: int


class Metricas(BaseModel):
    total: int
    pendientes: int
    contactados: int
    en_grupo: int
    tasa_conversion: float  # sumados / contactados, en porcentaje
