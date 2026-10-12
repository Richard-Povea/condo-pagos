from sqlalchemy import text
from condo_pagos.infrastructure.database.engine import SessionLocal

ESQUEMA_VERSION_ESPERADA = 1


def verificar_esquema() -> None:
    """Verifica que la base de datos esté inicializada en la versión correcta del esquema."""
    with SessionLocal() as session:
        try:
            result = session.execute(
                text("SELECT version FROM gc.schema_info")
            ).scalar_one_or_none()
        except Exception as e:
            raise RuntimeError(
                "La tabla gc.schema_info no existe o no se pudo acceder al esquema de base de datos."
            ) from e

        if result is None or result != ESQUEMA_VERSION_ESPERADA:
            version_actual = result if result is not None else "desconocida"
            raise RuntimeError(
                f"La base de datos está en versión {version_actual} y la aplicación requiere {ESQUEMA_VERSION_ESPERADA}."
            )