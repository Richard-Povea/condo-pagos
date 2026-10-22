"""Contrato mínimo de los seeds de desarrollo para el esquema v2."""

import pytest
from sqlalchemy import text

from tests.integration.seed_ids import PAGO_SEMILLA_ANULADO, PAGO_SEMILLA_SIN_REFERENCIA
from condo_pagos.infrastructure.database.schema import ESQUEMA_VERSION_ESPERADA

pytestmark = pytest.mark.integration


def test_seeds_cargan_version_operador_referencia_nula_y_anulacion_valida(engine) -> None:
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
                WHERE id = :pago_id
                  AND referencia IS NULL
                """
            ),
            {"pago_id": PAGO_SEMILLA_SIN_REFERENCIA},
        ).scalar_one()
        assert pago_sin_referencia == "ADMIN_DEMO"

        pago_anulado = connection.execute(
            text(
                """
                SELECT estado, anulado_en, anulado_por, motivo_anulacion, registrado_por
                FROM gc.pagos
                WHERE id = :pago_id
                """
            ),
            {"pago_id": PAGO_SEMILLA_ANULADO},
        ).one()
        assert pago_anulado.estado == "ANULADO"
        assert pago_anulado.anulado_en is not None
        assert pago_anulado.anulado_por == "ADMIN_DEMO"
        assert len(pago_anulado.motivo_anulacion.strip()) >= 10
        assert pago_anulado.registrado_por == "ADMIN_DEMO"
