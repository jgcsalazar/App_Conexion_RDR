"""Contraseña compartida para toda la app (HTTP Basic Auth).

No hay usuarios individuales: todo el equipo entra con la misma contraseña,
que se define en la variable de entorno APP_PASSWORD. El navegador muestra
su propio cuadro de usuario/contraseña — no hace falta programar un login.

El nombre de usuario no se valida (podés poner cualquier cosa); lo único
que importa es la contraseña.
"""

import os
import secrets

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

# Rutas que quedan afuera de la contraseña: Railway necesita pegarle a /health
# sin autenticarse para saber si el servicio sigue vivo.
RUTAS_PUBLICAS = {"/health"}


class ContraseñaCompartidaMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        password = os.getenv("APP_PASSWORD")

        # Si no se configuró ninguna contraseña, la app queda abierta (útil
        # para desarrollo local). En producción, definí APP_PASSWORD.
        if not password or request.url.path in RUTAS_PUBLICAS:
            return await call_next(request)

        cabecera = request.headers.get("authorization", "")
        if cabecera.startswith("Basic "):
            import base64

            try:
                decodificado = base64.b64decode(cabecera[6:]).decode("utf-8")
                _usuario, _, intento = decodificado.partition(":")
            except Exception:
                intento = ""
        else:
            intento = ""

        if secrets.compare_digest(intento, password):
            return await call_next(request)

        return JSONResponse(
            {"detail": "Contraseña incorrecta o faltante"},
            status_code=401,
            headers={"WWW-Authenticate": 'Basic realm="Conexión"'},
        )
