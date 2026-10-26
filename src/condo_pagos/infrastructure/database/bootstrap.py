"""Compatibilidad para la verificación del esquema con engine explícito."""

from sqlalchemy import Engine

from condo_pagos.infrastructure.database.schema import (
    ESQUEMA_VERSION_ESPERADA,
)
from condo_pagos.infrastructure.database.schema import (
    verificar_esquema as _verificar_esquema,
)

__all__ = ["ESQUEMA_VERSION_ESPERADA", "verificar_esquema"]


def verificar_esquema(engine: Engine) -> None:
    """Verifica el esquema usando el engine entregado por la raíz de composición."""
    _verificar_esquema(engine)
