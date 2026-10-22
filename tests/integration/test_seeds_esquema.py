"""Contrato mínimo de los seeds de desarrollo para el esquema v2."""

import pytest
from sqlalchemy import text

from condo_pagos.infrastructure.database.engine import engine
from condo_pagos.infrastructure.database.schema import ESQUEMA_VERSION_ESPERADA

pytestmark = pytest.mark.integration


def test_seeds_cargan_version_operador_referencia_nula_y_anulacion_valida() -> None:
    with engine.connect() as connection:
        version = connection.execute(
            text("SELECT version FROM gc.schema_info")
        ).scalar_one()
        assert version == ESQUEMA_VERSION_ESPERADA == 2

        pago_sin_referencia = connection.execute(
            text(
                """
                SELECT registrado_por
                FROM gc.pagos
                WHERE id = '44444444-4444-4444-4444-444444444444'
                  AND referencia IS NULL
                """
            )
        ).scalar_one()
        assert pago_sin_referencia == "ADMIN_DEMO"

        pago_anulado = connection.execute(
            text(
                """
                SELECT estado, anulado_en, anulado_por, motivo_anulacion, registrado_por
                FROM gc.pagos
                WHERE id = '66666666-6666-6666-6666-666666666666'
                """
            )
        ).one()
        assert pago_anulado.estado == "ANULADO"
        assert pago_anulado.anulado_en is not None
        assert pago_anulado.anulado_por == "ADMIN_DEMO"
        assert len(pago_anulado.motivo_anulacion.strip()) >= 10
        assert pago_anulado.registrado_por == "ADMIN_DEMO"
