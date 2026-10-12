import pytest
from PySide6.QtCore import QThreadPool
from condo_pagos.ui.viewmodels.base import BaseViewModel

class DummyViewModel(BaseViewModel):
    def __init__(self, pool: QThreadPool | None = None, parent = None) -> None:
        super().__init__(pool, parent)
        # Declaración explícita para satisfacer al tipador estático
        self.ultimo_resultado: str | None = None

    def ejecutar_tarea_mock(self, exito: bool = True):
        def tarea_lenta():
            if not exito:
                raise ValueError("Error simulado")
            return "resultado_exitoso"

        self._ejecutar(
            tarea_lenta,
            on_ok=lambda res: setattr(self, "ultimo_resultado", res)
        )

@pytest.mark.unit
def test_viewmodel_estado_ocupado_y_senal(qtbot):
    vm = DummyViewModel()
    assert not vm.ocupado

    estados_ocupado = []
    vm.ocupado_cambio.connect(lambda val: estados_ocupado.append(val))

    vm.ejecutar_tarea_mock(exito=True)
    
    # Esperar con qtbot a que termine la tarea del worker
    qtbot.waitUntil(lambda: not vm.ocupado, timeout=1000)

    assert vm.ultimo_resultado == "resultado_exitoso"
    assert True in estados_ocupado
    assert estados_ocupado[-1] is False