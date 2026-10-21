"""Validación de la versión del esquema antes de abrir la interfaz."""

from sqlalchemy import Engine, text
from sqlalchemy.exc import OperationalError, ProgrammingError, SQLAlchemyError

from condo_pagos.infrastructure.errors import ErrorDeInfraestructura, EsquemaIncompatible

ESQUEMA_VERSION_ESPERADA = 1


def verificar_esquema(engine: Engine) -> None:
    """Comprueba conectividad y compatibilidad del esquema PostgreSQL."""
    try:
        with engine.connect() as connection:
            version = connection.execute(
                text("SELECT version FROM gc.schema_info")
            ).scalar_one_or_none()
    except OperationalError as exc:
        raise ErrorDeInfraestructura() from exc
    except ProgrammingError as exc:
        raise EsquemaIncompatible(
            "La base de datos no tiene el esquema instalado o no es compatible."
        ) from exc
    except SQLAlchemyError as exc:
        raise ErrorDeInfraestructura(
            "No se pudo verificar la base de datos. Intente nuevamente o avise al administrador."
        ) from exc

    if version != ESQUEMA_VERSION_ESPERADA:
        version_texto = "desconocida" if version is None else str(version)
        raise EsquemaIncompatible(
            f"La base de datos está en la versión {version_texto} y la aplicación "
            f"requiere la versión {ESQUEMA_VERSION_ESPERADA}."
        )
