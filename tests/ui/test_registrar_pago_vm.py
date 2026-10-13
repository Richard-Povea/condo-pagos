from decimal import Decimal

import pytest

from condo_pagos.ui.viewmodels.registrar_pago_vm import RegistrarPagoViewModel


class UnidadMock:
    def __init__(self, unidad_id, identificador):
        self.unidad_id = unidad_id
        self.identificador = identificador

@pytest.mark.unit
def test_vm_validacion_monto_excede_deuda():
    # Arrange: Mock de casos de uso vacíos/fakes
    vm = RegistrarPagoViewModel(
        buscar_unidades_uc=lambda texto: [],
        consultar_estado_uc=lambda uid: None,
        registrar_pago_uc=lambda **kwargs: None
    )
    
    mensajes_error = []
    vm.error_campo.connect(lambda campo, msg: mensajes_error.append((campo, msg)))

    deuda_total = Decimal("100000")

    # Act & Assert: Intentar ingresar un monto mayor a la deuda
    vm.validar_y_actualizar_monto("150.000", deuda_total)
    
    assert len(mensajes_error) > 0
    assert mensajes_error[-1][0] == "monto"
    assert "supera la deuda" in mensajes_error[-1][1]

@pytest.mark.unit
def test_vm_debounce_y_stale_responses(qtbot):
    # Simula múltiples búsquedas rápidas donde solo la última debe ser procesada
    resultados_recibidos = []

    def buscar_lento(texto):
        return [UnidadMock("1", texto)]

    vm = RegistrarPagoViewModel(
        buscar_unidades_uc=buscar_lento,
        consultar_estado_uc=lambda uid: None,
        registrar_pago_uc=lambda **kwargs: None
    )
    vm.resultado_busqueda.connect(lambda res: resultados_recibidos.append(res))

    # Escribir de forma rápida consecutiva
    vm.buscar_unidades("Depto 1")
    vm.buscar_unidades("Depto 10")
    vm.buscar_unidades("Depto 101")

    qtbot.waitUntil(lambda: len(resultados_recibidos) > 0, timeout=1000)
    
    # Comprobar que solo la última respuesta o la última token válida es la que prevalece
    assert resultados_recibidos[-1][0].identificador == "Depto 101"