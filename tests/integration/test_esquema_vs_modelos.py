"""Comprueba que los modelos SQLAlchemy no diverjan del esquema PostgreSQL."""

import pytest
from sqlalchemy import DateTime, Enum as SAEnum, Numeric, String, inspect, text
from sqlalchemy.dialects.postgresql import ENUM

from condo_pagos.infrastructure.database.engine import engine
from condo_pagos.infrastructure.database.models import Base
from condo_pagos.infrastructure.database.schema import ESQUEMA_VERSION_ESPERADA

pytestmark = pytest.mark.integration


def test_modelos_coinciden_con_el_esquema() -> None:
    inspector = inspect(engine)
    problemas: list[str] = []
    tablas_modelo = {tabla.name for tabla in Base.metadata.sorted_tables}
    tablas_db = set(inspector.get_table_names(schema="gc"))
    tablas_sin_modelo = tablas_db - tablas_modelo - {"schema_info"}
    if tablas_sin_modelo:
        problemas.append(
            f"Tablas en gc sin modelo SQLAlchemy: {sorted(tablas_sin_modelo)}"
        )

    for tabla in Base.metadata.sorted_tables:
        columnas_db = {
            columna["name"]: columna
            for columna in inspector.get_columns(tabla.name, schema="gc")
        }

        for columna_modelo in tabla.columns:
            nombre = columna_modelo.name
            if nombre not in columnas_db:
                problemas.append(f"{tabla.name}.{nombre}: no existe en la BD")
                continue

            columna_db = columnas_db[nombre]
            tipo_modelo = columna_modelo.type
            tipo_db = columna_db["type"]

            if isinstance(tipo_modelo, SAEnum):
                if not isinstance(tipo_db, ENUM):
                    problemas.append(
                        f"{tabla.name}.{nombre}: modelo ENUM vs BD {tipo_db!r}"
                    )
                elif tipo_modelo.name != tipo_db.name:
                    problemas.append(
                        f"{tabla.name}.{nombre}: enum modelo {tipo_modelo.name!r} "
                        f"vs BD {tipo_db.name!r}"
                    )
                else:
                    valores_modelo = list(tipo_modelo.enums)
                    valores_db = list(tipo_db.enums)
                    if valores_modelo != valores_db:
                        problemas.append(
                            f"{tabla.name}.{nombre}: valores enum modelo "
                            f"{valores_modelo!r} vs BD {valores_db!r}"
                        )
            else:
                try:
                    tipos_coinciden = tipo_modelo.python_type is tipo_db.python_type
                except (AttributeError, NotImplementedError):
                    tipos_coinciden = type(tipo_modelo) is type(tipo_db)

                if not tipos_coinciden:
                    problemas.append(
                        f"{tabla.name}.{nombre}: modelo {tipo_modelo!r} "
                        f"vs BD {tipo_db!r}"
                    )

            if isinstance(tipo_modelo, String) and not isinstance(tipo_modelo, SAEnum):
                longitud_db = getattr(tipo_db, "length", None)
                if tipo_modelo.length != longitud_db:
                    problemas.append(
                        f"{tabla.name}.{nombre}: longitud modelo "
                        f"{tipo_modelo.length!r} vs BD {longitud_db!r}"
                    )

            if isinstance(tipo_modelo, Numeric):
                precision_db = getattr(tipo_db, "precision", None)
                escala_db = getattr(tipo_db, "scale", None)
                if (tipo_modelo.precision, tipo_modelo.scale) != (
                    precision_db,
                    escala_db,
                ):
                    problemas.append(
                        f"{tabla.name}.{nombre}: precisión/escala modelo "
                        f"({tipo_modelo.precision}, {tipo_modelo.scale}) vs BD "
                        f"({precision_db}, {escala_db})"
                    )

            if isinstance(tipo_modelo, DateTime):
                zona_modelo = tipo_modelo.timezone
                zona_db = getattr(tipo_db, "timezone", None)
                if zona_modelo != zona_db:
                    problemas.append(
                        f"{tabla.name}.{nombre}: timezone modelo {zona_modelo!r} "
                        f"vs BD {zona_db!r}"
                    )

            if columna_modelo.nullable != columna_db["nullable"]:
                problemas.append(
                    f"{tabla.name}.{nombre}: nullable modelo "
                    f"{columna_modelo.nullable} vs BD {columna_db['nullable']}"
                )

        columnas_modelo = {columna.name for columna in tabla.columns}
        sobrantes = set(columnas_db) - columnas_modelo
        if sobrantes:
            problemas.append(
                f"{tabla.name}: columnas en BD sin modelo: {sorted(sobrantes)}"
            )

    assert not problemas, "\n".join(problemas)


def test_version_de_esquema_instalada() -> None:
    with engine.connect() as connection:
        version = connection.execute(
            text("SELECT version FROM gc.schema_info")
        ).scalar_one_or_none()

    assert version == ESQUEMA_VERSION_ESPERADA == 2
