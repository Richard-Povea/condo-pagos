"""Prueba unicidad por condominio/método, referencias opcionales y pagos anulados."""

from datetime import UTC, date, datetime
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

pytestmark = pytest.mark.integration


def _insertar_unidad(connection, unidad_id, condominio_id, codigo: str) -> None:
    connection.execute(
        text(
            """
            INSERT INTO gc.unidades (id, condominio_id, codigo, condominio_nombre, activa)
            VALUES (:id, :condominio_id, :codigo, 'Condominio prueba índice', TRUE)
            """
        ),
        {"id": unidad_id, "condominio_id": condominio_id, "codigo": codigo},
    )


def _insertar_pago(
    connection,
    *,
    pago_id,
    unidad_id,
    condominio_id,
    metodo: str,
    referencia: str | None,
    folio: str,
    estado: str = "VIGENTE",
    anulado_en=None,
    anulado_por=None,
    motivo_anulacion=None,
) -> None:
    connection.execute(
        text(
            """
            INSERT INTO gc.pagos (
                id, unidad_id, condominio_id, monto, metodo_pago, referencia,
                residente_nombre, registrado_por, fecha, folio, exceso, estado,
                anulado_en, anulado_por, motivo_anulacion
            )
            VALUES (
                :id, :unidad_id, :condominio_id, 1000, :metodo, :referencia,
                'Residente prueba', 'OPERADOR_TEST', :fecha, :folio, 0, :estado,
                :anulado_en, :anulado_por, :motivo_anulacion
            )
            """
        ),
        {
            "id": pago_id,
            "unidad_id": unidad_id,
            "condominio_id": condominio_id,
            "metodo": metodo,
            "referencia": referencia,
            "fecha": date.today(),
            "folio": folio,
            "estado": estado,
            "anulado_en": anulado_en,
            "anulado_por": anulado_por,
            "motivo_anulacion": motivo_anulacion,
        },
    )


def test_referencias_opcionales_y_unicidad_por_condominio_y_metodo(engine) -> None:
    unidad_1, unidad_2 = uuid4(), uuid4()
    condominio_1, condominio_2 = uuid4(), uuid4()
    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            _insertar_unidad(connection, unidad_1, condominio_1, "IDX-101")
            _insertar_unidad(connection, unidad_2, condominio_2, "IDX-201")

            # Dos referencias NULL están permitidas.
            _insertar_pago(
                connection, 
                pago_id=uuid4(), 
                unidad_id=unidad_1, 
                condominio_id=condominio_1,
                metodo="EFECTIVO", 
                referencia=None, 
                folio="IDX-001")
            _insertar_pago(
                connection, 
                pago_id=uuid4(), 
                unidad_id=unidad_1, 
                condominio_id=condominio_1,
                metodo="EFECTIVO", 
                referencia=None, 
                folio="IDX-002")

            # Misma referencia en un método diferente: permitido.
            transferencia_id = uuid4()
            _insertar_pago(connection, pago_id=transferencia_id, unidad_id=unidad_1,
                           condominio_id=condominio_1, metodo="TRANSFERENCIA",
                           referencia="REF-UNICA", folio="IDX-003")
            _insertar_pago(connection, pago_id=uuid4(), unidad_id=unidad_1,
                           condominio_id=condominio_1, metodo="EFECTIVO",
                           referencia="REF-UNICA", folio="IDX-004")

            # Misma referencia y método en el mismo condominio: rechazado.
            with pytest.raises(IntegrityError), connection.begin_nested():
                _insertar_pago(connection, pago_id=uuid4(), unidad_id=unidad_1,
                               condominio_id=condominio_1, metodo="TRANSFERENCIA",
                               referencia="REF-UNICA", folio="IDX-005")

            # Misma referencia y método en otro condominio: permitido.
            _insertar_pago(connection, pago_id=uuid4(), unidad_id=unidad_2,
                           condominio_id=condominio_2, metodo="TRANSFERENCIA",
                           referencia="REF-UNICA", folio="IDX-006")

            # Tras anular correctamente, la referencia se puede reutilizar.
            connection.execute(
                text(
                    """
                    UPDATE gc.pagos
                    SET estado = 'ANULADO',
                        anulado_en = now(),
                        anulado_por = 'OPERADOR_TEST',
                        motivo_anulacion = 'Anulación válida para prueba'
                    WHERE id = :id
                    """
                ),
                {"id": transferencia_id},
            )
            _insertar_pago(connection, pago_id=uuid4(), unidad_id=unidad_1,
                           condominio_id=condominio_1, metodo="TRANSFERENCIA",
                           referencia="REF-UNICA", folio="IDX-007")
        finally:
            transaction.rollback()


def test_fk_compuesta_y_check_de_auditoria_de_anulacion(engine) -> None:
    unidad_id, condominio_id, otro_condominio = uuid4(), uuid4(), uuid4()
    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            _insertar_unidad(connection, unidad_id, condominio_id, "IDX-FK")

            with pytest.raises(IntegrityError), connection.begin_nested():
                _insertar_pago(
                    connection, pago_id=uuid4(), unidad_id=unidad_id,
                    condominio_id=otro_condominio, metodo="EFECTIVO",
                    referencia=None, folio="IDX-FK-BAD",
                )

            with pytest.raises(IntegrityError), connection.begin_nested():
                _insertar_pago(
                    connection, pago_id=uuid4(), unidad_id=unidad_id,
                    condominio_id=condominio_id, metodo="EFECTIVO",
                    referencia=None, folio="IDX-ANULADO-SIN-OP",
                    estado="ANULADO", anulado_en=datetime(2026, 10, 20, 12, 0, tzinfo=UTC),
                    anulado_por=None, motivo_anulacion="Motivo suficientemente largo",
                )

            with pytest.raises(IntegrityError), connection.begin_nested():
                _insertar_pago(
                    connection, pago_id=uuid4(), unidad_id=unidad_id,
                    condominio_id=condominio_id, metodo="EFECTIVO",
                    referencia=None, folio="IDX-ANULADO-MOT-CORT",
                    estado="ANULADO", anulado_en="2026-10-20T12:00:00Z",
                    anulado_por="OPERADOR_TEST", motivo_anulacion="corto",
                )

            with pytest.raises(IntegrityError), connection.begin_nested():
                _insertar_pago(
                    connection, pago_id=uuid4(), unidad_id=unidad_id,
                    condominio_id=condominio_id, metodo="EFECTIVO",
                    referencia=None, folio="IDX-VIGENTE-AUDIT",
                    estado="VIGENTE", anulado_en="2026-10-20T12:00:00Z",
                    anulado_por="OPERADOR_TEST",
                    motivo_anulacion="Motivo suficientemente largo",
                )
        finally:
            transaction.rollback()
