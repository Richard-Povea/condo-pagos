"""Smoke tests de la raíz única de composición con una base privada por prueba."""

import pytest

from condo_pagos.bootstrap import build_container
from condo_pagos.config import Settings


@pytest.mark.integration
def test_e2e_registro_pago_y_generacion_pdf(tmp_path, engine):
    """Registra un pago mediante el contrato público y genera su comprobante."""
    settings = Settings(
        condo_database_url=engine.url.render_as_string(hide_password=False),
        pdf_dir=tmp_path,
    )
    container = build_container(settings)

    try:
        unidades = container.listar_unidades()
        assert unidades, "Los seeds deben proporcionar al menos una unidad"

        resultado = container.registrar_pago(
            unidad_id=unidades[0].id,
            monto="1.00",
            metodo_pago="EFECTIVO",
            operador="test-e2e",
        )

        assert resultado.folio
        assert resultado.pdf_ok
        assert resultado.pdf_ruta is not None
        assert (tmp_path / f"comprobante_{resultado.folio}.pdf").is_file()
    finally:
        container.cerrar()


@pytest.mark.integration
def test_e2e_contenedor_usado_por_la_ui(tmp_path, engine):
    """Comprueba que la UI y el smoke test usan la misma raíz de composición."""
    settings = Settings(
        condo_database_url=engine.url.render_as_string(hide_password=False),
        pdf_dir=tmp_path,
    )
    container = build_container(settings)

    try:
        assert container.listar_unidades()
        assert container.listar_pagos().total_paginas >= 0
        assert callable(container.registrar_pago)
        assert callable(container.anular_pago)
        assert callable(container.emitir_pdf)
    finally:
        container.cerrar()
