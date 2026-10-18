from decimal import Decimal

import pytest

from condo_pagos.infrastructure.memory_container import InMemoryContainer


def test_contenedor_demo_inicia_con_unidades() -> None:
    container = InMemoryContainer()

    unidades = container.listar_unidades()

    assert len(unidades) == 3
    assert container.nombre_condominio.endswith("(Demo)")


def test_registrar_pago_actualiza_saldo_y_aparece_en_historial() -> None:
    container = InMemoryContainer()
    unidad = container.listar_unidades()[0]
    saldo_inicial = unidad.saldo_total

    resultado = container.registrar_pago(
        unidad_id=unidad.unidad_id,
        monto=Decimal("10000"),
        metodo_pago="EFECTIVO",
        referencia="DEMO-REF-1",
        operador="Prueba",
    )

    assert resultado.folio == "DEMO-000001"
    assert unidad.saldo_total == saldo_inicial - Decimal("10000")
    pagos = container.listar_pagos().filas
    assert len(pagos) == 1
    assert pagos[0].referencia == "DEMO-REF-1"


def test_demo_rechaza_pago_superior_a_la_deuda() -> None:
    container = InMemoryContainer()
    unidad = container.listar_unidades()[0]

    with pytest.raises(ValueError, match="más que la deuda"):
        container.registrar_pago(
            unidad_id=unidad.unidad_id,
            monto=Decimal("999999"),
            referencia="DEMO-REF-2",
        )


def test_anular_pago_restituye_saldo() -> None:
    container = InMemoryContainer()
    unidad = container.listar_unidades()[0]
    saldo_inicial = unidad.saldo_total
    resultado = container.registrar_pago(
        unidad_id=unidad.unidad_id,
        monto=Decimal("10000"),
        referencia="DEMO-REF-3",
    )

    container.anular_pago(pago_id=str(resultado.pago_id), motivo="Prueba de anulación")

    assert unidad.saldo_total == saldo_inicial
    assert container.listar_pagos().filas[0].estado == "Anulado"
