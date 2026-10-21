"""Errores técnicos traducidos a mensajes seguros para la interfaz."""

from condo_pagos.use_cases.errors import ErrorDeAplicacion


class ErrorDeInfraestructura(ErrorDeAplicacion):
    """Representa un fallo técnico recuperable de infraestructura."""

    def __init__(
        self,
        mensaje: str = (
            "No se pudo conectar con la base de datos. "
            "Verifique la red o avise al administrador."
        ),
    ) -> None:
        super().__init__(mensaje)


class EsquemaIncompatible(ErrorDeAplicacion):
    """La base de datos no tiene el esquema que esta versión necesita."""
