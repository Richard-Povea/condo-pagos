import pytest
from PySide6.QtWidgets import QApplication

from condo_pagos.ui.components.base import CampoMonto, ChipEstado, Tarjeta


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app

def test_instanciar_componentes(qapp):
    tarjeta = Tarjeta("Título Test")
    assert tarjeta is not None

    monto = CampoMonto()
    assert monto is not None

    chip = ChipEstado("Pagado")
    assert chip is not None