"""Pruebas unitarias de las fábricas SQLAlchemy sin abrir conexiones reales."""

import condo_pagos.infrastructure.database.engine as database_engine


def test_modulo_no_expone_engine_ni_sessionlocal_globales() -> None:
    assert not hasattr(database_engine, "engine")
    assert not hasattr(database_engine, "Session" + "Local")


def test_fabrica_crea_engine_y_session_factory_inyectables() -> None:
    url = "postgresql+psycopg://usuario:clave@localhost:5432/base_prueba"
    engine = database_engine.crear_engine(url)

    try:
        session_factory = database_engine.crear_session_factory(engine)
        assert session_factory.kw["bind"] is engine
        assert session_factory.kw["expire_on_commit"] is False
    finally:
        engine.dispose()
