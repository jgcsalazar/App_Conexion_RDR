"""API de contactos para grupos de conexión.

Arrancar:  uvicorn app.main:app --reload
Docs:      http://127.0.0.1:8000/docs
"""

import csv
import io
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import models, schemas
from .auth import ContraseñaCompartidaMiddleware
from .database import Base, engine, get_db

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Contactos · grupos de conexión", version="1.0.0")
app.add_middleware(ContraseñaCompartidaMiddleware)


@app.get("/health", include_in_schema=False)
def salud():
    """Railway pega acá para saber si el servicio sigue vivo."""
    return {"estado": "ok"}

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

# Cada resultado de llamada deja al contacto en un estado. "reprogramar" no lo
# mueve: sigue en la cola tal como estaba.
ESTADO_SEGUN_RESULTADO = {
    models.Resultado.sin_respuesta: models.Estado.sin_respuesta,
    models.Resultado.interesado: models.Estado.interesado,
    models.Resultado.sumado: models.Estado.sumado,
    models.Resultado.no_interesado: models.Estado.no_interesado,
}


def buscar_contacto(db: Session, contacto_id: int) -> models.Contacto:
    contacto = db.get(models.Contacto, contacto_id)
    if contacto is None:
        raise HTTPException(404, "No existe ese contacto")
    return contacto


# ---------------------------------------------------------------- contactos

@app.post("/api/contactos", response_model=schemas.ContactoLeer, status_code=201)
def crear_contacto(datos: schemas.ContactoCrear, db: Session = Depends(get_db)):
    existente = db.scalar(
        select(models.Contacto).where(models.Contacto.telefono == datos.telefono)
    )
    if existente:
        raise HTTPException(409, f"Ese teléfono ya está cargado como {existente.nombre}")

    contacto = models.Contacto(**datos.model_dump())
    db.add(contacto)
    db.commit()
    db.refresh(contacto)
    return contacto


@app.get("/api/contactos", response_model=list[schemas.ContactoLeer])
def listar_contactos(
    db: Session = Depends(get_db),
    estado: models.Estado | None = None,
    grupo_id: int | None = None,
    buscar: str | None = Query(None, description="Busca por nombre o teléfono"),
):
    consulta = select(models.Contacto).order_by(models.Contacto.creado_en.desc())
    if estado:
        consulta = consulta.where(models.Contacto.estado == estado)
    if grupo_id:
        consulta = consulta.where(models.Contacto.grupo_id == grupo_id)
    if buscar:
        patron = f"%{buscar}%"
        consulta = consulta.where(
            models.Contacto.nombre.ilike(patron) | models.Contacto.telefono.ilike(patron)
        )
    return db.scalars(consulta).all()


@app.get("/api/contactos/cola", response_model=list[schemas.ContactoLeer])
def cola_de_llamados(db: Session = Depends(get_db), solo_autorizados: bool = True):
    """A quién llamar hoy: pendientes y sin respuesta, los más viejos primero."""
    consulta = (
        select(models.Contacto)
        .where(
            models.Contacto.estado.in_(
                [models.Estado.pendiente, models.Estado.sin_respuesta]
            )
        )
        .order_by(models.Contacto.creado_en)
    )
    if solo_autorizados:
        consulta = consulta.where(models.Contacto.autoriza_contacto.is_(True))
    return db.scalars(consulta).all()


@app.get("/api/contactos/{contacto_id}", response_model=schemas.ContactoLeer)
def ver_contacto(contacto_id: int, db: Session = Depends(get_db)):
    return buscar_contacto(db, contacto_id)


@app.patch("/api/contactos/{contacto_id}", response_model=schemas.ContactoLeer)
def actualizar_contacto(
    contacto_id: int, datos: schemas.ContactoActualizar, db: Session = Depends(get_db)
):
    contacto = buscar_contacto(db, contacto_id)
    for campo, valor in datos.model_dump(exclude_unset=True).items():
        setattr(contacto, campo, valor)
    db.commit()
    db.refresh(contacto)
    return contacto


@app.delete("/api/contactos/{contacto_id}", status_code=204)
def borrar_contacto(contacto_id: int, db: Session = Depends(get_db)):
    db.delete(buscar_contacto(db, contacto_id))
    db.commit()


# ---------------------------------------------------------------- llamadas

@app.post(
    "/api/contactos/{contacto_id}/llamadas",
    response_model=schemas.ContactoLeer,
    status_code=201,
)
def registrar_llamada(
    contacto_id: int, datos: schemas.LlamadaCrear, db: Session = Depends(get_db)
):
    """Deja constancia del intento y mueve el estado del contacto en consecuencia."""
    contacto = buscar_contacto(db, contacto_id)

    if datos.resultado == models.Resultado.sumado:
        grupo_id = datos.grupo_id or contacto.grupo_id
        if grupo_id is None:
            raise HTTPException(400, "Indicá a qué grupo se suma")
        grupo = db.get(models.Grupo, grupo_id)
        if grupo is None:
            raise HTTPException(404, "No existe ese grupo")
        if grupo.cupo_disponible == 0:
            raise HTTPException(409, f"{grupo.nombre} no tiene cupo disponible")
        contacto.grupo_id = grupo_id

    contacto.llamadas.append(
        models.Llamada(
            resultado=datos.resultado,
            comentario=datos.comentario,
            llamado_por=datos.llamado_por,
        )
    )
    nuevo_estado = ESTADO_SEGUN_RESULTADO.get(datos.resultado)
    if nuevo_estado:
        contacto.estado = nuevo_estado

    db.commit()
    db.refresh(contacto)
    return contacto


@app.put("/api/contactos/{contacto_id}/grupo", response_model=schemas.ContactoLeer)
def asignar_grupo(
    contacto_id: int, datos: schemas.AsignarGrupo, db: Session = Depends(get_db)
):
    """Suma al contacto al grupo elegido de la lista. Valida el cupo."""
    contacto = buscar_contacto(db, contacto_id)
    grupo = db.get(models.Grupo, datos.grupo_id)
    if grupo is None:
        raise HTTPException(404, "No existe ese grupo")
    if not grupo.activo:
        raise HTTPException(409, f"{grupo.nombre} no está activo")
    if contacto.grupo_id != grupo.id and grupo.cupo_disponible == 0:
        raise HTTPException(409, f"{grupo.nombre} no tiene cupo disponible")

    contacto.grupo_id = grupo.id
    contacto.estado = models.Estado.sumado
    db.commit()
    db.refresh(contacto)
    return contacto


@app.delete("/api/contactos/{contacto_id}/grupo", response_model=schemas.ContactoLeer)
def quitar_grupo(contacto_id: int, db: Session = Depends(get_db)):
    """Lo saca del grupo y lo devuelve a la cola como interesado."""
    contacto = buscar_contacto(db, contacto_id)
    contacto.grupo_id = None
    if contacto.estado == models.Estado.sumado:
        contacto.estado = models.Estado.interesado
    db.commit()
    db.refresh(contacto)
    return contacto


# ---------------------------------------------------------------- grupos

@app.post("/api/grupos", response_model=schemas.GrupoLeer, status_code=201)
def crear_grupo(datos: schemas.GrupoCrear, db: Session = Depends(get_db)):
    grupo = models.Grupo(**datos.model_dump())
    db.add(grupo)
    db.commit()
    db.refresh(grupo)
    return grupo


@app.get("/api/grupos", response_model=list[schemas.GrupoLeer])
def listar_grupos(db: Session = Depends(get_db)):
    return db.scalars(select(models.Grupo).order_by(models.Grupo.nombre)).all()


@app.patch("/api/grupos/{grupo_id}", response_model=schemas.GrupoLeer)
def actualizar_grupo(
    grupo_id: int, datos: schemas.GrupoActualizar, db: Session = Depends(get_db)
):
    grupo = db.get(models.Grupo, grupo_id)
    if grupo is None:
        raise HTTPException(404, "No existe ese grupo")
    for campo, valor in datos.model_dump(exclude_unset=True).items():
        setattr(grupo, campo, valor)
    db.commit()
    db.refresh(grupo)
    return grupo


# ---------------------------------------------------------------- métricas y export

@app.get("/api/metricas", response_model=schemas.Metricas)
def metricas(db: Session = Depends(get_db)):
    total = db.scalar(select(func.count(models.Contacto.id))) or 0
    pendientes = (
        db.scalar(
            select(func.count(models.Contacto.id)).where(
                models.Contacto.estado == models.Estado.pendiente
            )
        )
        or 0
    )
    en_grupo = (
        db.scalar(
            select(func.count(models.Contacto.id)).where(
                models.Contacto.grupo_id.is_not(None)
            )
        )
        or 0
    )
    contactados = total - pendientes
    tasa = round(en_grupo / contactados * 100, 1) if contactados else 0.0
    return schemas.Metricas(
        total=total,
        pendientes=pendientes,
        contactados=contactados,
        en_grupo=en_grupo,
        tasa_conversion=tasa,
    )


@app.get("/api/contactos.csv")
def exportar_csv(db: Session = Depends(get_db)):
    contactos = db.scalars(select(models.Contacto).order_by(models.Contacto.id)).all()
    buffer = io.StringIO()
    escritor = csv.writer(buffer)
    escritor.writerow(
        ["id", "nombre", "telefono", "email", "zona", "origen",
         "horario_preferido", "estado", "autoriza_contacto", "grupo", "notas", "alta"]
    )
    for c in contactos:
        escritor.writerow([
            c.id, c.nombre, c.telefono, c.email or "", c.zona or "",
            c.origen.value, c.horario_preferido.value, c.estado.value,
            "si" if c.autoriza_contacto else "no",
            c.grupo.nombre if c.grupo else "",
            (c.notas or "").replace("\n", " "),
            c.creado_en.strftime("%Y-%m-%d"),
        ])
    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="contactos.csv"'},
    )


# ---------------------------------------------------------------- frontend

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
def home():
    return FileResponse(STATIC_DIR / "index.html")
