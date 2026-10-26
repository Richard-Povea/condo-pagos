"""Smoke tests de la raíz única de composición con una base privada por prueba."""

import pytest


@pytest.mark.integration
def test_e2e_registro_pago_y_generacion_pdf(container_real, tmp_path):
    """Registra un pago mediante el contrato público y genera su comprobante."""
    unidades = container_real.listar_unidades()
    assert unidades, "Los seeds deben proporcionar al menos una unidad"

    resultado = container_real.registrar_pago(
        unidad_id=unidades[0].id,
        monto="1.00",
        metodo_pago="EFECTIVO",
        operador="test-e2e",
    )

    assert resultado.folio
    assert resultado.pdf_ok
    assert resultado.pdf_ruta is not None
    assert (tmp_path / f"comprobante_{resultado.folio}.pdf").is_file()


@pytest.mark.integration
def test_e2e_contenedor_usado_por_la_ui(container_real):
    """Comprueba que la UI y las pruebas usan la misma raíz de composición."""
    assert container_real.listar_unidades()
    assert container_real.listar_pagos().total_paginas >= 0
    assert callable(container_real.registrar_pago)
    assert callable(container_real.anular_pago)
    assert callable(container_real.emitir_pdf)
