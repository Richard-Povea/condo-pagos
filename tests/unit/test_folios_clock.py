"""Pruebas deterministas del reloj usado para asignar el año del folio."""

from datetime import datetime
from unittest.mock import Mock
from zoneinfo import ZoneInfo

from condo_pagos.infrastructure.database.unit_of_work import SqlAlchemyFoliosRepository


def test_folio_usa_reloj_y_zona_horaria_configurados() -> None:
    session = Mock()
    session.execute.return_value.scalar_one.return_value = 7
    zonas_recibidas: list[str] = []

    def reloj(zona: ZoneInfo) -> datetime:
        zonas_recibidas.append(zona.key)
        return datetime(2031, 1, 1, tzinfo=zona)

    repositorio = SqlAlchemyFoliosRepository(
        session,
        zona_horaria="Pacific/Kiritimati",
        reloj=reloj,
    )

    assert repositorio.siguiente_folio() == "2031-000007"
    assert zonas_recibidas == ["Pacific/Kiritimati"]
    assert session.execute.call_args.args[1] == {"anio": "2031"}
