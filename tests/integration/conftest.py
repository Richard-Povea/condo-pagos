"""Fixtures de integración con una base PostgreSQL aislada por prueba."""

import os
import uuid
from pathlib import Path

import psycopg
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from condo_pagos.infrastructure.database.unit_of_work import SqlAlchemyUnitOfWork

DB_DIR = Path(__file__).resolve().parents[2] / "db"
BASE_URL = make_url(
    os.environ.get(
        "CONDO_TEST_DATABASE_URL",
        "postgresql+psycopg://condo_test:condo_test_pw@localhost:5433/condo_test",
    )
)
PLANTILLA = f"condo_plantilla_{os.environ.get('PYTEST_XDIST_WORKER', 'master')}"


def _admin_engine():
    """Conecta a la base de mantenimiento para crear/eliminar bases de datos."""
    return create_engine(
        BASE_URL.set(database="postgres"),
        isolation_level="AUTOCOMMIT",
        pool_pre_ping=True,
    )


@pytest.fixture(scope="session")
def plantilla_db():
    """Construye una plantilla limpia aplicando el esquema y los seeds versionados."""
    admin = _admin_engine()
    try:
        with admin.connect() as connection:
            connection.execute(text(f'DROP DATABASE IF EXISTS "{PLANTILLA}" WITH (FORCE)'))
            connection.execute(text(f'CREATE DATABASE "{PLANTILLA}"'))

        dsn = BASE_URL.set(
            drivername="postgresql",
            database=PLANTILLA,
        ).render_as_string(hide_password=False)

        try:
            with psycopg.connect(dsn, autocommit=True) as connection:
                for filename in ("01-schema.sql", "02-seeds.sql"):
                    connection.execute((DB_DIR / filename).read_text(encoding="utf-8"))
        except Exception:
            with admin.connect() as connection:
                connection.execute(
                    text(f'DROP DATABASE IF EXISTS "{PLANTILLA}" WITH (FORCE)')
                )
            raise

        # La conexión a la plantilla queda cerrada antes de clonar bases desde ella.
        yield PLANTILLA
    finally:
        with admin.connect() as connection:
            connection.execute(text(f'DROP DATABASE IF EXISTS "{PLANTILLA}" WITH (FORCE)'))
        admin.dispose()


@pytest.fixture
def engine(plantilla_db):
    """Entrega una base privada por prueba, clonada con esquema y seeds."""
    nombre = f"condo_t_{uuid.uuid4().hex[:12]}"
    admin = _admin_engine()
    test_engine = None
    try:
        with admin.connect() as connection:
            connection.execute(
                text(f'CREATE DATABASE "{nombre}" TEMPLATE "{plantilla_db}"')
            )

        test_engine = create_engine(
            BASE_URL.set(database=nombre),
            pool_size=10,
            max_overflow=5,
            pool_pre_ping=True,
        )
        yield test_engine
    finally:
        if test_engine is not None:
            test_engine.dispose()
        with admin.connect() as connection:
            connection.execute(
                text(f'DROP DATABASE IF EXISTS "{nombre}" WITH (FORCE)')
            )
        admin.dispose()


@pytest.fixture
def session_local(engine):
    """Fábrica de sesiones ligada exclusivamente a la base de esta prueba."""
    return sessionmaker(bind=engine, expire_on_commit=False, future=True)


@pytest.fixture
def uow(session_local):
    """Unit of Work ligado a la base privada de la prueba."""
    return SqlAlchemyUnitOfWork(session_local)
