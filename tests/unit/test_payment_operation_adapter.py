from datetime import date
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

from condo_pagos.infrastructure.database import payment_operations as adapter_module
from condo_pagos.infrastructure.database.payment_operations import OperacionesPagoPostgres


class FakeSession:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return None

    def execute(self, statement, params):
        return SimpleNamespace(fetchone=lambda: SimpleNamespace(codigo="101"))


def _adapter() -> OperacionesPagoPostgres:
    return OperacionesPagoPostgres(
        session_factory=FakeSession,
        uow_factory=lambda: object(),  # type: ignore[arg-type]
        pdf_dir=Path("unused-test-pdfs"),
    )


def test_operador_vacio_se_rechaza_antes_de_acceder_a_la_base() -> None:
    called = False

    def session_factory():
        nonlocal called
        called = True
        return FakeSession()

    adapter = OperacionesPagoPostgres(
        session_factory=session_factory,  # type: ignore[arg-type]
        uow_factory=lambda: object(),  # type: ignore[arg-type]
        pdf_dir=Path("unused-test-pdfs"),
    )

    with pytest.raises(ValueError, match="operador"):
        adapter.registrar_pago(
            unidad_id=uuid4(),
            monto=1000,
            operador="   ",
        )

    assert called is False


def test_referencia_vacia_se_normaliza_a_none_y_fecha_se_conserva(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured = {}

    class FakeRegistrarPagoUseCase:
        def __init__(self, uow):
            pass

        def ejecutar(self, cmd):
            captured["cmd"] = cmd
            return SimpleNamespace(
                folio="2026-000001",
                monto_pagado=Decimal("1000"),
                pdf_ruta=None,
            )

    monkeypatch.setattr(
        adapter_module, "RegistrarPagoUseCase", FakeRegistrarPagoUseCase
    )
    adapter = _adapter()
    monkeypatch.setattr(adapter, "emitir_pdf", lambda folio: "/tmp/comprobante.pdf")

    fecha_pago = date(2026, 10, 21)
    adapter.registrar_pago(
        unidad_id=uuid4(),
        monto=1000,
        referencia="   ",
        operador="Administración",
        fecha=fecha_pago,
    )

    cmd = captured["cmd"]
    assert cmd.referencia is None
    assert cmd.fecha_pago == fecha_pago


def test_fallo_pdf_no_anula_pago_y_devuelve_pdf_ok_false(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeRegistrarPagoUseCase:
        def __init__(self, uow):
            pass

        def ejecutar(self, cmd):
            return SimpleNamespace(
                folio="2026-000002",
                monto_pagado=Decimal("1000"),
                pdf_ruta=None,
            )

    monkeypatch.setattr(
        adapter_module, "RegistrarPagoUseCase", FakeRegistrarPagoUseCase
    )

    def falla_pdf(folio: str) -> str:
        raise OSError("disco sin espacio")

    adapter = _adapter()
    monkeypatch.setattr(adapter, "emitir_pdf", falla_pdf)

    resultado = adapter.registrar_pago(
        unidad_id=uuid4(),
        monto=1000,
        referencia="TRANSFER-123",
        operador="Administración",
    )

    assert resultado.folio == "2026-000002"
    assert resultado.pdf_ok is False
    assert resultado.pdf_ruta is None
