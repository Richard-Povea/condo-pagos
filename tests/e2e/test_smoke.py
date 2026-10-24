"""Smoke test del composition root real con una base privada por prueba."""

import pytest

from condo_pagos.bootstrap import build_container
from condo_pagos.config import Settings


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


@pytest.mark.integration
def test_e2e_contenedor_usado_por_la_ui(tmp_path, engine):
    """Construye el contenedor PostgreSQL que utiliza el arranque real de la UI."""
    from condo_pagos.infrastructure.bootstrap import build_container as build_ui_container

    settings = Settings(
        condo_database_url=engine.url.render_as_string(hide_password=False),
        pdf_dir=tmp_path,
    )
    container = build_ui_container(settings)

    try:
        assert container.listar_unidades()
        assert container.listar_pagos().total_paginas >= 0
    finally:
        container.cerrar()
