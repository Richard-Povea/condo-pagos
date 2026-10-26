"""Comprueba la deriva entre metadatos SQLAlchemy y el esquema PostgreSQL real."""

import re

import pytest
from sqlalchemy import CHAR, DateTime, Numeric, String, inspect, text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import ENUM, JSONB

from condo_pagos.infrastructure.database.models import Base
from condo_pagos.infrastructure.database.schema import ESQUEMA_VERSION_ESPERADA

pytestmark = pytest.mark.integration


def _normalizar_sql(value: str) -> str:
    value = re.sub(r"\s+", " ", value)
    # Los paréntesis de agrupación no afectan esta comparación textual.
    value = value.replace("(", " ").replace(")", " ")

    # Normalizar operadores de varios caracteres antes de "=".
    value = re.sub(r"\s*(>=|<=|<>|!=)\s*", r" \1 ", value)
    value = re.sub(r"\s*=\s*", " = ", value)

    # Simplificar conversiones de tipos que PostgreSQL agrega al mostrar
    # las definiciones de restricciones e índices.
    value = re.sub(r"::[a-zA-Z_][a-zA-Z0-9_]*(?:\[\])?", "", value)

    value = re.sub(r"\s*,\s*", ", ", value)
    return re.sub(r"\s+", " ", value).strip()


def _deriva_esquema(connection) -> list[str]:
    inspector = inspect(connection)
    problemas: list[str] = []
    tablas_modelo = {tabla.name for tabla in Base.metadata.sorted_tables}
    tablas_db = set(inspector.get_table_names(schema="gc"))
    tablas_sin_modelo = tablas_db - tablas_modelo - {"schema_info"}
    if tablas_sin_modelo:
        problemas.append(f"Tablas en gc sin modelo SQLAlchemy: {sorted(tablas_sin_modelo)}")

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
                    problemas.append(f"{tabla.name}.{nombre}: modelo ENUM vs BD {tipo_db!r}")
                elif (
                    tipo_modelo.name != tipo_db.name
                    or list(tipo_modelo.enums) != list(tipo_db.enums)
                ):
                    problemas.append(
                        f"{tabla.name}.{nombre}: enum modelo ({tipo_modelo.name}, "
                        f"{list(tipo_modelo.enums)!r}) vs BD "
                        f"({tipo_db.name}, {list(tipo_db.enums)!r})"
                    )
            else:
                try:
                    tipos_coinciden = tipo_modelo.python_type is tipo_db.python_type
                except (AttributeError, NotImplementedError):
                    tipos_coinciden = type(tipo_modelo) is type(tipo_db)
                if not tipos_coinciden:
                    problemas.append(
                        f"{tabla.name}.{nombre}: modelo {tipo_modelo!r} vs BD {tipo_db!r}"
                    )

            if isinstance(tipo_modelo, String) and not isinstance(tipo_modelo, SAEnum):
                if isinstance(tipo_modelo, CHAR) != isinstance(tipo_db, CHAR):
                    problemas.append(
                        f"{tabla.name}.{nombre}: CHAR/VARCHAR modelo {type(tipo_modelo).__name__} "
                        f"vs BD {type(tipo_db).__name__}"
                    )
                longitud_db = getattr(tipo_db, "length", None)
                if tipo_modelo.length != longitud_db:
                    problemas.append(
                        f"{tabla.name}.{nombre}: longitud modelo {tipo_modelo.length!r} "
                        f"vs BD {longitud_db!r}"
                    )

            if isinstance(tipo_modelo, JSONB) and not isinstance(tipo_db, JSONB):
                problemas.append(f"{tabla.name}.{nombre}: se esperaba JSONB, BD tiene {tipo_db!r}")

            if isinstance(tipo_modelo, Numeric):
                precision_db = getattr(tipo_db, "precision", None)
                escala_db = getattr(tipo_db, "scale", None)
                if (tipo_modelo.precision, tipo_modelo.scale) != (precision_db, escala_db):
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
                    f"{tabla.name}.{nombre}: nullable modelo {columna_modelo.nullable} "
                    f"vs BD {columna_db['nullable']}"
                )

        columnas_modelo = {columna.name for columna in tabla.columns}
        sobrantes = set(columnas_db) - columnas_modelo
        if sobrantes:
            problemas.append(f"{tabla.name}: columnas en BD sin modelo: {sorted(sobrantes)}")

        # FKs: comparar las columnas locales/remotas en orden, no solo que exista alguna FK.
        fks_modelo = {
            (
                tuple(col.name for col in fk.columns),
                fk.referred_table.name,
                tuple(element.column.name for element in fk.elements),
            )
            for fk in tabla.foreign_key_constraints
        }
        fks_db = {
            (
                tuple(fk["constrained_columns"]),
                fk["referred_table"].split(".")[-1],
                tuple(fk["referred_columns"]),
            )
            for fk in inspector.get_foreign_keys(tabla.name, schema="gc")
        }
        for fk in fks_modelo - fks_db:
            problemas.append(f"{tabla.name}: falta FK esperada {fk!r}")
        for fk in fks_db - fks_modelo:
            problemas.append(f"{tabla.name}: FK extra en BD {fk!r}")

        # UNIQUE constraints, incluidos los pares (id, condominio_id).
        unique_modelo = {
            (constraint.name, tuple(col.name for col in constraint.columns))
            for constraint in tabla.constraints
            if constraint.__class__.__name__ == "UniqueConstraint"
        }
        unique_db = {
            (constraint.get("name"), tuple(constraint["column_names"]))
            for constraint in inspector.get_unique_constraints(tabla.name, schema="gc")
        }
        for unique in unique_modelo - unique_db:
            problemas.append(f"{tabla.name}: falta UNIQUE {unique!r}")
        for unique in unique_db - unique_modelo:
            problemas.append(f"{tabla.name}: UNIQUE extra en BD {unique!r}")

        # CHECK: comparar la definición del catálogo PostgreSQL con la metadata.
        checks_modelo = {
            constraint.name: _normalizar_sql(str(constraint.sqltext))
            for constraint in tabla.constraints
            if constraint.__class__.__name__ == "CheckConstraint" and constraint.name
        }
        checks_db = {
            check["name"]: _normalizar_sql(check["sqltext"])
            for check in inspector.get_check_constraints(tabla.name, schema="gc")
            if check.get("name")
        }
        for nombre, definicion in checks_modelo.items():
            if nombre not in checks_db:
                problemas.append(f"{tabla.name}: falta CHECK {nombre}")
            elif checks_db[nombre] != definicion:
                problemas.append(
                    f"{tabla.name}: CHECK {nombre} difiere: modelo={definicion!r}, "
                    f"BD={checks_db[nombre]!r}"
                )
        for nombre in checks_db.keys() - checks_modelo.keys():
            problemas.append(f"{tabla.name}: CHECK extra en BD {nombre}")

        # Índices: comparar nombre, columnas, unicidad y predicado completo.
        indices_modelo = {index.name: index for index in tabla.indexes}
        indices_db = {
            index["name"]: index
            for index in inspector.get_indexes(tabla.name, schema="gc")
            if not index.get("duplicates_constraint")
        }
        for nombre, index_modelo in indices_modelo.items():
            index_db = indices_db.get(nombre)
            if index_db is None:
                problemas.append(f"{tabla.name}: falta índice {nombre}")
                continue
            columnas_modelo_idx = tuple(col.name for col in index_modelo.columns)
            columnas_db_idx = tuple(index_db.get("column_names") or ())
            if columnas_modelo_idx != columnas_db_idx:
                problemas.append(
                    f"{tabla.name}: índice {nombre} columnas modelo={columnas_modelo_idx!r}, "
                    f"BD={columnas_db_idx!r}"
                )
            if bool(index_modelo.unique) != bool(index_db.get("unique")):
                problemas.append(f"{tabla.name}: índice {nombre} difiere en unique")

            where_modelo = index_modelo.dialect_options["postgresql"].get("where")
            where_db = index_db.get("dialect_options", {}).get("postgresql_where")
            if where_modelo is None and where_db is not None:
                problemas.append(
                    f"{tabla.name}: índice {nombre} tiene predicado inesperado "
                    f"{where_db!r}"
                )
            elif where_modelo is not None and (
                where_db is None
                or _normalizar_sql(str(where_modelo)) != _normalizar_sql(str(where_db))
            ):
                problemas.append(
                    f"{tabla.name}: predicado de {nombre} difiere: "
                    f"modelo={str(where_modelo)!r}, BD={where_db!r}"
                )

        for nombre in indices_db.keys() - indices_modelo.keys():
            problemas.append(f"{tabla.name}: índice extra en BD {nombre}")

    # Verificación explícita de la definición que devuelve PostgreSQL para el índice parcial.
    indexdef = connection.execute(
        text("SELECT pg_get_indexdef('gc.uq_pagos_referencia'::regclass)")
    ).scalar_one_or_none()
    if indexdef is None:
        problemas.append("pagos: no existe uq_pagos_referencia en pg_get_indexdef")
    else:
        match = re.search(r"using\s+\w+\s+\((.*?)\)\s+where\s+(.*)$", indexdef, re.I)
        if not match:
            problemas.append(f"pagos: no se pudo interpretar pg_get_indexdef: {indexdef}")
        else:
            columnas = tuple(part.strip().strip('"') for part in match.group(1).split(","))
            if columnas != ("condominio_id", "metodo_pago", "referencia"):
                problemas.append(
                    "pagos: columnas de uq_pagos_referencia incorrectas: "
                    f"{columnas!r}"
                )
            if _normalizar_sql(match.group(2)) != _normalizar_sql(
                "referencia IS NOT NULL AND estado = 'VIGENTE'"
            ):
                problemas.append(f"pagos: predicado incorrecto en pg_get_indexdef: {indexdef}")

    # Comparación explícita con pg_get_constraintdef para el CHECK de anulación.
    check_db = connection.execute(
        text(
            """
            SELECT pg_get_constraintdef(oid)
            FROM pg_constraint
            WHERE conrelid = 'gc.pagos'::regclass
              AND conname = 'ck_pagos_anulacion'
            """
        )
    ).scalar_one_or_none()
    check_modelo = next(
        str(constraint.sqltext)
        for constraint in Base.metadata.tables["pagos"].constraints
        if constraint.name == "ck_pagos_anulacion"
    )
    if check_db is None:
        problemas.append("pagos: falta ck_pagos_anulacion en pg_get_constraintdef")
    elif _normalizar_sql(check_db.removeprefix("CHECK ")) != _normalizar_sql(check_modelo):
        problemas.append(
            "pagos: pg_get_constraintdef difiere para ck_pagos_anulacion: "
            f"{check_db}"
        )

    # Comprobar columnas, orden y tabla destino de la FK compuesta.
    fk_compuesta = connection.execute(
        text(
            """
            SELECT
                c.conname,
                c.confrelid::regclass::text AS tabla_destino,
                ARRAY(
                    SELECT a.attname
                    FROM unnest(c.conkey) WITH ORDINALITY AS k(attnum, ord)
                    JOIN pg_attribute a
                    ON a.attrelid = c.conrelid
                    AND a.attnum = k.attnum
                    ORDER BY k.ord
                ) AS columnas_origen,
                ARRAY(
                    SELECT a.attname
                    FROM unnest(c.confkey) WITH ORDINALITY AS k(attnum, ord)
                    JOIN pg_attribute a
                    ON a.attrelid = c.confrelid
                    AND a.attnum = k.attnum
                    ORDER BY k.ord
                ) AS columnas_destino
            FROM pg_constraint c
            WHERE c.conrelid = 'gc.pagos'::regclass
            AND c.conname = 'fk_pagos_unidad_condominio'
            AND c.contype = 'f'
            """
        )
    ).one_or_none()

    if fk_compuesta is None:
        problemas.append("pagos: falta fk_pagos_unidad_condominio")
    else:
        _, tabla_destino, columnas_origen, columnas_destino = fk_compuesta

        if columnas_origen != ["unidad_id", "condominio_id"]:
            problemas.append(
                f"pagos: columnas de origen incorrectas en FK compuesta: "
                f"{columnas_origen!r}"
            )

        if tabla_destino not in ("unidades", "gc.unidades"):
            problemas.append(
                f"pagos: tabla destino incorrecta en FK compuesta: "
                f"{tabla_destino!r}"
            )

        if columnas_destino != ["id", "condominio_id"]:
            problemas.append(
                f"pagos: columnas destino incorrectas en FK compuesta: "
                f"{columnas_destino!r}"
            )

    # Confirmación explícita mediante pg_get_constraintdef para las nuevas reglas.
    checks_nuevos = {
        ("cargos", "ck_cargos_monto"),
        ("cargos", "ck_cargos_saldo"),
        ("pagos", "ck_pagos_monto"),
        ("pagos", "ck_pagos_exceso"),
    }
    for tabla, nombre in checks_nuevos:
        definicion_db = connection.execute(
            text(
                """
                SELECT pg_get_constraintdef(oid)
                FROM pg_constraint
                WHERE conrelid = CAST(:tabla AS regclass)
                  AND conname = :nombre
                  AND contype = 'c'
                """
            ),
            {"tabla": f"gc.{tabla}", "nombre": nombre},
        ).scalar_one_or_none()
        modelo = next(
            (
                str(constraint.sqltext)
                for constraint in Base.metadata.tables[tabla].constraints
                if constraint.name == nombre
            ),
            None,
        )
        if definicion_db is None:
            problemas.append(f"{tabla}: falta {nombre} en pg_get_constraintdef")
        elif modelo is None or (
            _normalizar_sql(definicion_db.removeprefix("CHECK "))
            != _normalizar_sql(modelo)
        ):
            problemas.append(
                f"{tabla}: pg_get_constraintdef difiere para {nombre}: {definicion_db}"
            )

    fk_comprobante = connection.execute(
        text(
            """
            SELECT pg_get_constraintdef(oid)
            FROM pg_constraint
            WHERE conrelid = 'gc.comprobantes'::regclass
              AND conname = 'fk_comprobantes_pago'
              AND contype = 'f'
            """
        )
    ).scalar_one_or_none()
    if fk_comprobante is None:
        problemas.append("comprobantes: falta fk_comprobantes_pago en pg_get_constraintdef")
    elif _normalizar_sql(fk_comprobante) != _normalizar_sql(
        "FOREIGN KEY (folio) REFERENCES gc.pagos(folio)"
    ):
        problemas.append(
            "comprobantes: definición incorrecta de fk_comprobantes_pago: "
            f"{fk_comprobante}"
        )

    return problemas


def test_modelos_coinciden_con_el_esquema(engine) -> None:
    with engine.connect() as connection:
        problemas = _deriva_esquema(connection)
    assert not problemas, "\\n".join(problemas)


def test_version_de_esquema_instalada(engine) -> None:
    with engine.connect() as connection:
        version = connection.execute(
            text("SELECT version FROM gc.schema_info")
        ).scalar_one_or_none()
    assert version == ESQUEMA_VERSION_ESPERADA == 2


def _mutacion_falla(ddls: str | list[str], engine) -> None:
    sentencias = [ddls] if isinstance(ddls, str) else ddls
    with engine.connect() as connection:
        transaccion = connection.begin()
        try:
            for ddl in sentencias:
                connection.execute(text(ddl))
            problemas = _deriva_esquema(connection)
            assert problemas, f"La deriva no detectó la mutación: {sentencias}"
        finally:
            transaccion.rollback()


def test_deriva_detecta_indice_sin_condominio_id(engine) -> None:
    _mutacion_falla([
        "DROP INDEX gc.uq_pagos_referencia",
        "CREATE UNIQUE INDEX uq_pagos_referencia ON gc.pagos (metodo_pago, referencia) "
        "WHERE referencia IS NOT NULL AND estado = 'VIGENTE'",
    ], engine)


def test_deriva_detecta_longitud_anulado_por_incorrecta(engine) -> None:
    _mutacion_falla("ALTER TABLE gc.pagos ALTER COLUMN anulado_por TYPE VARCHAR(100)", engine)


def test_deriva_detecta_fecha_date_convertida_a_timestamptz(engine) -> None:
    _mutacion_falla(
        "ALTER TABLE gc.pagos ALTER COLUMN fecha TYPE TIMESTAMPTZ USING fecha::timestamptz",
        engine,
    )


def test_deriva_detecta_fk_compuesta_ausente(engine) -> None:
    _mutacion_falla("ALTER TABLE gc.pagos DROP CONSTRAINT fk_pagos_unidad_condominio", engine)


def test_deriva_detecta_predicado_de_indice_modificado(engine) -> None:
    _mutacion_falla([
        "DROP INDEX gc.uq_pagos_referencia",
        "CREATE UNIQUE INDEX uq_pagos_referencia ON gc.pagos "
        "(condominio_id, metodo_pago, referencia) WHERE referencia IS NOT NULL",
    ], engine)


def test_deriva_detecta_nulabilidad_incorrecta(engine) -> None:
    _mutacion_falla("ALTER TABLE gc.pagos ALTER COLUMN condominio_id DROP NOT NULL", engine)


def test_deriva_detecta_hash_sha256_que_deja_de_ser_char_64(engine) -> None:
    _mutacion_falla(
        "ALTER TABLE gc.comprobantes ALTER COLUMN hash_sha256 TYPE VARCHAR(64) "
        "USING hash_sha256::varchar(64)",
        engine,
    )


def test_deriva_detecta_check_de_anulacion_ausente(engine) -> None:
    _mutacion_falla("ALTER TABLE gc.pagos DROP CONSTRAINT ck_pagos_anulacion", engine)


def test_deriva_detecta_enum_metodo_pago_ausente(engine) -> None:
    _mutacion_falla([
        "ALTER TABLE gc.pagos DROP CONSTRAINT ck_pagos_referencia_requerida",
        "ALTER TABLE gc.pagos ALTER COLUMN metodo_pago TYPE VARCHAR(50) USING metodo_pago::text",
        "DROP TYPE gc.metodo_pago_enum",
    ], engine)


def test_deriva_detecta_check_referencia_requerida_ausente(engine) -> None:
    _mutacion_falla(
        "ALTER TABLE gc.pagos DROP CONSTRAINT ck_pagos_referencia_requerida",
        engine,
    )


def test_deriva_detecta_check_referencia_no_vacia_ausente(engine) -> None:
    _mutacion_falla(
        "ALTER TABLE gc.pagos DROP CONSTRAINT ck_pagos_referencia_no_vacia",
        engine,
    )


def test_deriva_detecta_check_saldo_cargo_ausente(engine) -> None:
    _mutacion_falla("ALTER TABLE gc.cargos DROP CONSTRAINT ck_cargos_saldo", engine)


def test_deriva_detecta_fk_comprobante_pago_ausente(engine) -> None:
    _mutacion_falla(
        "ALTER TABLE gc.comprobantes DROP CONSTRAINT fk_comprobantes_pago",
        engine,
    )
