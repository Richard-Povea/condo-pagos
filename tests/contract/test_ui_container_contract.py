"""Contrato compartido de registro e historial para demo y PostgreSQL real."""

from decimal import Decimal
from typing import Any

import pytest

from condo_pagos.infrastructure.memory_container import InMemoryContainer


def _verificar_registro_e_historial(container: Any) -> None:
    unidades = container.listar_unidades()
    assert unidades, "El contenedor debe exponer al menos una unidad"

    unidad = unidades[0]
    estado_antes = container.consultar_estado_cuenta(unidad.id)
    assert estado_antes.total_adeudado > 0

    monto = min(estado_antes.total_adeudado, Decimal("1.00"))
    resultado = container.registrar_pago(
        unidad_id=unidad.id,
        monto=monto,
        metodo_pago="EFECTIVO",
        operador="test-contract",
    )

    estado_despues = container.consultar_estado_cuenta(unidad.id)
    historial = container.listar_pagos()
    assert estado_despues.total_adeudado == estado_antes.total_adeudado - monto
    assert any(pago.folio == resultado.folio for pago in historial.filas)


def test_contrato_registrar_pago_e_historial_en_memoria() -> None:
    container = InMemoryContainer()
    _verificar_registro_e_historial(container)
    container.cerrar()


@pytest.mark.integration
def test_contrato_registrar_pago_e_historial_en_postgres(container_real: Any) -> None:
    _verificar_registro_e_historial(container_real)
