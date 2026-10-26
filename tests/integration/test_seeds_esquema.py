"""Contrato mínimo de los seeds de desarrollo para el esquema v2."""

import pytest
from seed_ids import (
    CARGO_SEMILLA,
    PAGO_SEMILLA_ANULADO,
    PAGO_SEMILLA_SIN_REFERENCIA,
    PAGO_SEMILLA_SIN_REFERENCIA_2,
    PAGO_SEMILLA_TRANSFERENCIA,
    UNIDAD_SEMILLA_101,
    UNIDAD_SEMILLA_102,
)
from sqlalchemy import text

from condo_pagos.infrastructure.database.schema import ESQUEMA_VERSION_ESPERADA

pytestmark = pytest.mark.integration


def test_seeds_cargan_version_operador_referencia_nula_y_anulacion_valida(engine) -> None:
    with engine.connect() as connection:
        version = connection.execute(
            text("SELECT version FROM gc.schema_info")
        ).scalar_one()
        assert version == ESQUEMA_VERSION_ESPERADA == 2

        seeds_esperados = (
            ("gc.unidades", UNIDAD_SEMILLA_101),
            ("gc.unidades", UNIDAD_SEMILLA_102),
            ("gc.cargos", CARGO_SEMILLA),
            ("gc.pagos", PAGO_SEMILLA_SIN_REFERENCIA),
            ("gc.pagos", PAGO_SEMILLA_SIN_REFERENCIA_2),
            ("gc.pagos", PAGO_SEMILLA_ANULADO),
            ("gc.pagos", PAGO_SEMILLA_TRANSFERENCIA),
        )
        for tabla, seed_id in seeds_esperados:
            existe = connection.execute(
                text(f"SELECT EXISTS (SELECT 1 FROM {tabla} WHERE id = :seed_id)"),
                {"seed_id": seed_id},
            ).scalar_one()
            assert existe, f"Falta el seed {seed_id} en {tabla}"

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


def test_seed_transferencia_vigente_tiene_referencia(engine) -> None:
    with engine.connect() as connection:
        pago = connection.execute(
            text(
                "SELECT metodo_pago, referencia, estado FROM gc.pagos WHERE id = :pago_id"
            ),
            {"pago_id": PAGO_SEMILLA_TRANSFERENCIA},
        ).one()
    assert pago.metodo_pago == "TRANSFERENCIA"
    assert pago.referencia == "DEMO-REF-VIGENTE"
    assert pago.estado == "VIGENTE"
