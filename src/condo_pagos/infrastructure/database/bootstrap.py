"""Compatibilidad para el antiguo punto de entrada de verificación."""

from condo_pagos.infrastructure.database.engine import engine
from condo_pagos.infrastructure.database.schema import (
    ESQUEMA_VERSION_ESPERADA,
    verificar_esquema as _verificar_esquema,
)


def verificar_esquema() -> None:
    """Verifica el esquema usando el engine de configuración heredado."""
    _verificar_esquema(engine)
