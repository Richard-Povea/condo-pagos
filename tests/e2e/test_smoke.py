"""Smoke test del composition root real con una base privada por prueba."""

import pytest

from condo_pagos.config import Settings
from condo_pagos.bootstrap import build_container


@pytest.mark.integration
def test_e2e_registro_pago_y_generacion_pdf(tmp_path, engine):
    """Comprueba que el composition root construye los adaptadores reales."""
    settings = Settings(
        condo_database_url=engine.url.render_as_string(hide_password=False),
        pdf_dir=tmp_path,
    )
    container = build_container(settings)

    try:
        registrar_pago_uc = container.registrar_pago_use_case()
        assert registrar_pago_uc is not None
        assert container.pdf_renderer is not None
        assert container.storage is not None
    finally:
        container.cerrar()
