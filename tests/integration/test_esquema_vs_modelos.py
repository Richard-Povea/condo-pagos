"""Comprueba que los modelos SQLAlchemy no diverjan del esquema PostgreSQL."""
from sqlalchemy import Enum as SAEnum
from sqlalchemy import Numeric, String, inspect
from sqlalchemy.dialects.postgresql import ENUM

import pytest

from condo_pagos.infrastructure.database.engine import engine
from condo_pagos.infrastructure.database.models import Base

pytestmark = pytest.mark.integration


def test_modelos_coinciden_con_el_esquema() -> None:
    inspector = inspect(engine)
    problemas: list[str] = []

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

            # PostgreSQL devuelve los ENUM como texto en python_type; comparar
            # sus valores explícitamente evita un falso positivo con StrEnum.
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
