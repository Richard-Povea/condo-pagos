"""Verifica las reglas de unicidad para referencias opcionales."""

from datetime import date
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from condo_pagos.infrastructure.database.engine import engine


pytestmark = pytest.mark.integration


def test_referencias_opcionales_y_unicidad_solo_en_pagos_vigentes() -> None:
    unidad_id = uuid4()
    pago_efectivo_1 = uuid4()
    pago_efectivo_2 = uuid4()
    pago_transferencia_1 = uuid4()
    pago_transferencia_2 = uuid4()

    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            connection.execute(
                text(
                    "INSERT INTO gc.unidades "
                    "(id, condominio_id, codigo, condominio_nombre, activa) "
                    "VALUES (:id, :condominio_id, :codigo, :nombre, TRUE)"
                ),
                {
                    "id": unidad_id,
                    "condominio_id": uuid4(),
                    "codigo": f"IDX-{str(unidad_id)[:8]}",
                    "nombre": "Condominio prueba índice",
                },
            )

            def insertar_pago(
                pago_id, metodo: str, referencia: str | None, folio: str, estado: str
            ) -> None:
                connection.execute(
                    text(
                        "INSERT INTO gc.pagos "
                        "(id, unidad_id, monto, metodo_pago, referencia, "
                        "residente_nombre, registrado_por, fecha, folio, exceso, estado) "
                        "VALUES (:id, :unidad_id, 1000, :metodo, :referencia, "
                        "'Residente prueba', 'OPERADOR_TEST', :fecha, :folio, 0, :estado)"
                    ),
                    {
                        "id": pago_id,
                        "unidad_id": unidad_id,
                        "metodo": metodo,
                        "referencia": referencia,
                        "fecha": date.today(),
                        "folio": folio,
                        "estado": estado,
                    },
                )

            insertar_pago(pago_efectivo_1, "EFECTIVO", None, "IDX-001", "VIGENTE")
            insertar_pago(pago_efectivo_2, "EFECTIVO", None, "IDX-002", "VIGENTE")
            insertar_pago(
                pago_transferencia_1, "TRANSFERENCIA", "REF-UNICA", "IDX-003", "VIGENTE"
            )

            with pytest.raises(IntegrityError):
                with connection.begin_nested():
                    insertar_pago(
                        pago_transferencia_2,
                        "TRANSFERENCIA",
                        "REF-UNICA",
                        "IDX-004",
                        "VIGENTE",
                    )

            connection.execute(
                text("UPDATE gc.pagos SET estado = 'ANULADO' WHERE id = :id"),
                {"id": pago_transferencia_1},
            )
            insertar_pago(
                pago_transferencia_2, "TRANSFERENCIA", "REF-UNICA", "IDX-004", "VIGENTE"
            )
        finally:
            transaction.rollback()
