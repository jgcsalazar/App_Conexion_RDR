"""Carga datos de ejemplo: dos grupos y tres contactos. Uso: python seed.py"""

from app.database import Base, SessionLocal, engine
from app.models import Contacto, Estado, Grupo, Horario, Origen

Base.metadata.create_all(bind=engine)
db = SessionLocal()

if db.query(Grupo).count() == 0:
    norte = Grupo(nombre="Grupo Norte", zona="Belgrano", dia_semana="martes",
                  horario="20:00", anfitrion="Sofía", cupo_maximo=10)
    centro = Grupo(nombre="Grupo Centro", zona="Palermo", dia_semana="jueves",
                   horario="19:30", anfitrion="Martín", cupo_maximo=12)
    db.add_all([norte, centro])
    db.flush()

    db.add_all([
        Contacto(nombre="Lucía Fernández", telefono="+54 9 11 5555 1234",
                 zona="Belgrano", origen=Origen.evento, horario_preferido=Horario.noche,
                 autoriza_contacto=True, grupo_id=norte.id),
        Contacto(nombre="Diego Paz", telefono="+54 9 11 4444 8899",
                 zona="Palermo", origen=Origen.referido, horario_preferido=Horario.tarde,
                 autoriza_contacto=True, notas="Lo trajo Martín."),
        Contacto(nombre="Carla Ruiz", telefono="+54 9 11 3333 7788",
                 origen=Origen.redes, horario_preferido=Horario.manana,
                 autoriza_contacto=True, estado=Estado.sumado, grupo_id=centro.id),
    ])
    db.commit()
    print("Datos de ejemplo cargados.")
else:
    print("La base ya tiene datos, no toco nada.")
db.close()
