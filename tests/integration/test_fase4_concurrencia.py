from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from decimal import Decimal
from threading import Barrier
from uuid import uuid4

import pytest
from seed_ids import PAGO_SEMILLA_SIN_REFERENCIA
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from condo_pagos.domain.entities import Cargo, EstadoCargo
from condo_pagos.domain.errors import DominioError, PagoYaAnuladoError
from condo_pagos.infrastructure.database.bootstrap import ESQUEMA_VERSION_ESPERADA
from condo_pagos.infrastructure.database.unit_of_work import SqlAlchemyUnitOfWork
from condo_pagos.use_cases.anular_pago import AnularPagoUseCase
from condo_pagos.use_cases.dto import RegistrarPagoCmd
from condo_pagos.use_cases.registrar_pago import RegistrarPagoUseCase

pytestmark = pytest.mark.integration


def _crear_unidad_y_cargo(uow, unidad_id, cargo_id, monto=Decimal("50000"), codigo="101"):
    with uow:
        uow.session.execute(
            text("""
                INSERT INTO gc.unidades (id, condominio_id, codigo, condominio_nombre, activa)
                VALUES (:id, :cond_id, :codigo, :nombre, :activa)
                ON CONFLICT (id) DO NOTHING
            """),
            {
                "id": str(unidad_id),
                "cond_id": str(uuid4()),
                "codigo": codigo,
                "nombre": "Condominio Concurrente",
                "activa": True,
            },
        )
        cargo = Cargo(
            id=cargo_id,
            unidad_id=unidad_id,
            periodo="2026-10",
            monto_original=monto,
            saldo=monto,
            vencimiento=date(2026, 10, 10),
            estado=EstadoCargo.PENDIENTE,
        )
        uow.cargos.guardar(cargo)
        uow.commit()


def test_1_folios_concurrentes(uow, session_local):
    """6 hilos pagando en distintas unidades producen folios [1..6] sin huecos ni duplicados."""
    unidades = [uuid4() for _ in range(6)]
    cargos = [uuid4() for _ in range(6)]

    # Preparar todas las unidades y cargos de forma síncrona y limpia.
    for i in range(6):
        uow_prep = SqlAlchemyUnitOfWork(session_local)
        _crear_unidad_y_cargo(uow_prep, unidades[i], cargos[i], codigo=str(200 + i))

    barrera = Barrier(6)

    def realizar_pago(idx):
        # Cada hilo abre su propia UoW y espera antes de iniciar la operación.
        barrera.wait(timeout=10)
        with SqlAlchemyUnitOfWork(session_local) as uow_hilo:
            caso_uso = RegistrarPagoUseCase(uow_hilo)
            cmd = RegistrarPagoCmd(
                unidad_id=unidades[idx],
                monto=Decimal("50000"),
                metodo_pago="TRANSFERENCIA",
                referencia=f"REF-CONC-{idx}",
                residente_nombre=f"Residente {idx}",
                registrado_por="OPERADOR_TEST",
                fecha_pago=date(2026, 10, 12),
            )
            return caso_uso.ejecutar(cmd).folio

    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = [executor.submit(realizar_pago, i) for i in range(6)]
        folios_obtenidos = [future.result() for future in as_completed(futures)]

    anio_actual = str(date.today().year)
    numeros = sorted(int(f.split("-")[1]) for f in folios_obtenidos)
    assert numeros == [1, 2, 3, 4, 5, 6]
    for folio in folios_obtenidos:
        assert folio.startswith(anio_actual)


def test_2_doble_pago_simultaneo_misma_unidad(session_local):
    """Doble pago simultáneo en la misma unidad: el segundo falla porque FOR UPDATE serializa."""
    unidad_id = uuid4()
    cargo_id = uuid4()
    uow_prep = SqlAlchemyUnitOfWork(session_local)
    _crear_unidad_y_cargo(uow_prep, unidad_id, cargo_id, monto=Decimal("50000"), codigo="301")
    barrera = Barrier(2)

    def intentar_pago(ref):
        uow = SqlAlchemyUnitOfWork(session_local)
        caso_uso = RegistrarPagoUseCase(uow)
        cmd = RegistrarPagoCmd(
            unidad_id=unidad_id,
            monto=Decimal("50000"),
            metodo_pago="TRANSFERENCIA",
            referencia=ref,
            residente_nombre="Simultáneo",
            registrado_por="OPERADOR_TEST",
            fecha_pago=date(2026, 10, 12),
        )
        barrera.wait(timeout=10)
        return caso_uso.ejecutar(cmd)

    exitos = 0
    errores = 0
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(intentar_pago, "REF-SIM-A"),
            executor.submit(intentar_pago, "REF-SIM-B"),
        ]
        for future in as_completed(futures):
            try:
                future.result()
                exitos += 1
            except DominioError:
                errores += 1

    assert exitos == 1
    assert errores == 1


def test_3_rollback_no_consume_folio(uow):
    """Forzar una falla después de obtener siguiente() y verificar que el contador no avanzó."""
    with uow:
        folio_antes = uow.folios.siguiente_folio()
        uow.rollback()

    with uow:
        folio_despues = uow.folios.siguiente_folio()

    assert folio_antes == folio_despues


def test_4_referencia_duplicada(uow):
    """Referencia duplicada lanza DominioError."""
    unidad_id = uuid4()
    cargo_id = uuid4()
    _crear_unidad_y_cargo(uow, unidad_id, cargo_id, codigo="401")

    cmd = RegistrarPagoCmd(
        unidad_id=unidad_id,
        monto=Decimal("50000"),
        metodo_pago="EFECTIVO",
        referencia="REF-DUP-TEST",
        residente_nombre="Duplicado",
        registrado_por="OPERADOR_TEST",
        fecha_pago=date(2026, 10, 12),
    )
    caso_uso = RegistrarPagoUseCase(uow)
    caso_uso.ejecutar(cmd)

    # Segundo intento con misma referencia.
    with pytest.raises(DominioError, match="Ya existe un pago registrado"):
        caso_uso.ejecutar(cmd)


def test_5_trigger_inmutabilidad(uow):
    """Un UPDATE de snapshot, hash o folio en comprobantes falla por el trigger."""
    unidad_id = uuid4()
    cargo_id = uuid4()
    _crear_unidad_y_cargo(uow, unidad_id, cargo_id, codigo="501")

    caso_uso = RegistrarPagoUseCase(uow)
    cmd = RegistrarPagoCmd(
        unidad_id=unidad_id,
        monto=Decimal("50000"),
        metodo_pago="TRANSFERENCIA",
        referencia="REF-IMMUTABLE",
        residente_nombre="Inmutable",
        registrado_por="OPERADOR_TEST",
        fecha_pago=date(2026, 10, 12),
    )
    resultado = caso_uso.ejecutar(cmd)

    # Intentar hacer UPDATE directo sobre la tabla comprobantes.
    with pytest.raises(Exception, match="inmutables"):
        uow.session.execute(
            text("UPDATE gc.comprobantes SET residente_nombre = 'Modificado' WHERE folio = :folio"),
            {"folio": resultado.folio},
        )
        uow.commit()


def test_6_constraints_check_y_fk(uow):
    """Verificar violaciones de integridad referencial (FK)."""
    with uow, pytest.raises(IntegrityError):
        uow.session.execute(
            text("""
                    INSERT INTO gc.cargos (
                    id, unidad_id, periodo, monto_original,
                    saldo, vencimiento, estado)
                    VALUES (:id, :unidad_id, '2026-10', 1000, 1000, '2026-10-10', 'PENDIENTE')
                """),
            {"id": str(uuid4()), "unidad_id": str(uuid4())},  # Unidad inexistente.
        )
        uow.commit()


def test_7_anulacion_restaura_saldos(uow):
    """La anulación restaura los saldos de los cargos y el folio sigue ocupado."""
    unidad_id = uuid4()
    cargo_id = uuid4()
    _crear_unidad_y_cargo(uow, unidad_id, cargo_id, monto=Decimal("50000"), codigo="701")

    pendientes_iniciales = uow.cargos.obtener_pendientes_por_unidad(unidad_id)
    assert len(pendientes_iniciales) == 1

    caso_uso_pago = RegistrarPagoUseCase(uow)
    cmd = RegistrarPagoCmd(
        unidad_id=unidad_id,
        monto=Decimal("50000"),
        metodo_pago="TRANSFERENCIA",
        referencia="REF-ANULAR-01",
        residente_nombre="Anular Test",
        registrado_por="OPERADOR_TEST",
        fecha_pago=date(2026, 10, 12),
    )
    _ = caso_uso_pago.ejecutar(cmd)

    pendientes_antes_anular = uow.cargos.obtener_pendientes_por_unidad(unidad_id)
    assert len(pendientes_antes_anular) == 0

    pago_db = uow.session.execute(
        text("SELECT id FROM gc.pagos WHERE referencia = 'REF-ANULAR-01'")
    ).fetchone()

    caso_uso_anular = AnularPagoUseCase(uow)
    caso_uso_anular.ejecutar(
        pago_db.id,
        operador="OPERADOR_TEST",
        motivo="Anulación de prueba para verificar restauración de saldos",
    )

    pendientes_despues = uow.cargos.obtener_pendientes_por_unidad(unidad_id)
    assert len(pendientes_despues) == 1
    assert pendientes_despues[0].saldo == Decimal("50000")


def test_8_plantilla_contiene_esquema_v2_y_seeds(engine):
    """La base clonada contiene la versión esperada y los seeds de contrato."""
    with engine.connect() as connection:
        version = connection.execute(text("SELECT version FROM gc.schema_info")).scalar_one()
        pago_semilla = connection.execute(
            text("SELECT 1 FROM gc.pagos WHERE id = :pago_id"),
            {"pago_id": PAGO_SEMILLA_SIN_REFERENCIA},
        ).scalar_one_or_none()

    assert version == ESQUEMA_VERSION_ESPERADA
    assert pago_semilla == 1

def _registrar_pago_de_prueba(session_local, unidad_id, referencia):
    with SqlAlchemyUnitOfWork(session_local) as uow:
        return RegistrarPagoUseCase(uow).ejecutar(
            RegistrarPagoCmd(
                unidad_id=unidad_id,
                monto=Decimal("50000"),
                metodo_pago="TRANSFERENCIA",
                referencia=referencia,
                residente_nombre="Residente de prueba",
                registrado_por="OPERADOR_TEST",
                fecha_pago=date(2026, 10, 12),
            )
        )


def test_doble_anulacion_simultanea(session_local, engine):
    """Dos anulaciones simultáneas restituyen el saldo una sola vez."""
    unidad_id, cargo_id = uuid4(), uuid4()
    with SqlAlchemyUnitOfWork(session_local) as uow:
        _crear_unidad_y_cargo(uow, unidad_id, cargo_id, monto=Decimal("50000"))
    pago = _registrar_pago_de_prueba(session_local, unidad_id, "REF-ANULACION-ATOMICA")
    with engine.connect() as connection:
        pago_id = connection.execute(
            text("SELECT id FROM gc.pagos WHERE folio = :folio"),
            {"folio": pago.folio},
        ).scalar_one()

    barrera = Barrier(2)

    def anular():
        barrera.wait(timeout=10)
        with SqlAlchemyUnitOfWork(session_local) as uow:
            AnularPagoUseCase(uow).ejecutar(
                pago_id,
                operador="OPERADOR_TEST",
                motivo="Motivo de prueba de concurrencia",
            )
        return "ok"

    exitos = 0
    errores = 0
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(anular) for _ in range(2)]
        for future in as_completed(futures):
            try:
                future.result()
                exitos += 1
            except PagoYaAnuladoError:
                errores += 1

    assert (exitos, errores) == (1, 1)
    with engine.connect() as connection:
        saldo, estado_cargo = connection.execute(
            text("SELECT saldo, estado FROM gc.cargos WHERE id = :id"),
            {"id": cargo_id},
        ).one()
        estado_pago = connection.execute(
            text("SELECT estado FROM gc.pagos WHERE id = :id"),
            {"id": pago_id},
        ).scalar_one()
    assert saldo == Decimal("50000")
    assert estado_cargo == "PENDIENTE"
    assert estado_pago == "ANULADO"


def test_anulacion_restaura_todos_los_cargos_del_comprobante(session_local, engine):
    unidad_id = uuid4()
    cargo_ids = [uuid4(), uuid4()]
    with SqlAlchemyUnitOfWork(session_local) as uow:
        _crear_unidad_y_cargo(uow, unidad_id, cargo_ids[0], monto=Decimal("30000"), codigo="801")
        _crear_unidad_y_cargo(uow, unidad_id, cargo_ids[1], monto=Decimal("20000"), codigo="801")

    with SqlAlchemyUnitOfWork(session_local) as uow:
        resultado = RegistrarPagoUseCase(uow).ejecutar(
            RegistrarPagoCmd(
                unidad_id=unidad_id,
                monto=Decimal("50000"),
                metodo_pago="TRANSFERENCIA",
                referencia="REF-MULTI-CARGO",
                residente_nombre="Residente multi cargo",
                registrado_por="OPERADOR_TEST",
                fecha_pago=date(2026, 10, 12),
            )
        )
    with engine.connect() as connection:
        pago_id = connection.execute(
            text("SELECT id FROM gc.pagos WHERE folio = :folio"),
            {"folio": resultado.folio},
        ).scalar_one()

    with SqlAlchemyUnitOfWork(session_local) as uow:
        AnularPagoUseCase(uow).ejecutar(
            pago_id, operador="OPERADOR_TEST",
            motivo="Anulación de pago distribuido entre cargos",
        )

    with engine.connect() as connection:
        cargos = connection.execute(
            text(
                "SELECT id, monto_original, saldo, estado "
                "FROM gc.cargos WHERE id = ANY(:ids) ORDER BY id"
            ),
            {"ids": cargo_ids},
        ).fetchall()
    assert len(cargos) == 2
    assert all(row.saldo == row.monto_original for row in cargos)
    assert all(row.estado == "PENDIENTE" for row in cargos)


def test_cargo_faltante_revierte_transaccion_de_anulacion(session_local, engine):
    unidad_id, cargo_id = uuid4(), uuid4()
    with SqlAlchemyUnitOfWork(session_local) as uow:
        _crear_unidad_y_cargo(uow, unidad_id, cargo_id, monto=Decimal("50000"))
    resultado = _registrar_pago_de_prueba(session_local, unidad_id, "REF-CARGO-FALTANTE")
    with engine.connect() as connection:
        pago_id = connection.execute(
            text("SELECT id FROM gc.pagos WHERE folio = :folio"),
            {"folio": resultado.folio},
        ).scalar_one()
    with engine.begin() as connection:
        connection.execute(text("DELETE FROM gc.cargos WHERE id = :id"), {"id": cargo_id})

    with pytest.raises(DominioError, match="No se encontró el cargo"):
        with SqlAlchemyUnitOfWork(session_local) as uow:
            AnularPagoUseCase(uow).ejecutar(
                pago_id, operador="OPERADOR_TEST",
                motivo="Anulación que debe fallar por cargo faltante",
            )

    with engine.connect() as connection:
        estado = connection.execute(
            text("SELECT estado FROM gc.pagos WHERE id = :id"),
            {"id": pago_id},
        ).scalar_one()
    assert estado == "VIGENTE"


def test_folio_no_se_reutiliza_despues_de_anular(session_local, engine):
    unidad_a, cargo_a = uuid4(), uuid4()
    unidad_b, cargo_b = uuid4(), uuid4()
    with SqlAlchemyUnitOfWork(session_local) as uow:
        _crear_unidad_y_cargo(uow, unidad_a, cargo_a, monto=Decimal("50000"), codigo="901")
        _crear_unidad_y_cargo(uow, unidad_b, cargo_b, monto=Decimal("50000"), codigo="902")

    primer_pago = _registrar_pago_de_prueba(session_local, unidad_a, "REF-FOLIO-UNO")
    with engine.connect() as connection:
        primer_id = connection.execute(
            text("SELECT id FROM gc.pagos WHERE folio = :folio"),
            {"folio": primer_pago.folio},
        ).scalar_one()
    with SqlAlchemyUnitOfWork(session_local) as uow:
        AnularPagoUseCase(uow).ejecutar(
            primer_id, operador="OPERADOR_TEST",
            motivo="Anulación para comprobar que no se reutiliza folio",
        )
    segundo_pago = _registrar_pago_de_prueba(session_local, unidad_b, "REF-FOLIO-DOS")
    assert int(segundo_pago.folio.split("-")[1]) == int(primer_pago.folio.split("-")[1]) + 1
    with engine.connect() as connection:
        comprobante = connection.execute(
            text("SELECT 1 FROM gc.comprobantes WHERE folio = :folio"),
            {"folio": primer_pago.folio},
        ).scalar_one_or_none()
    assert comprobante == 1


def test_checks_unique_y_fk_rechazan_sql_directo(session_local, engine):
    """Los constraints nuevos protegen también escrituras que omiten los casos de uso."""
    unidad_id, cargo_id = uuid4(), uuid4()
    with SqlAlchemyUnitOfWork(session_local) as uow:
        _crear_unidad_y_cargo(uow, unidad_id, cargo_id, monto=Decimal("50000"), codigo="991")
    with engine.connect() as connection:
        condominio_id = connection.execute(
            text("SELECT condominio_id FROM gc.unidades WHERE id = :id"),
            {"id": unidad_id},
        ).scalar_one()

    def assert_integrity_error(statement, params):
        with engine.connect() as connection:
            transaction = connection.begin()
            try:
                with pytest.raises(IntegrityError):
                    connection.execute(text(statement), params)
            finally:
                transaction.rollback()

    assert_integrity_error(
        "UPDATE gc.cargos SET saldo = monto_original + 1 WHERE id = :id",
        {"id": cargo_id},
    )
    assert_integrity_error(
        "UPDATE gc.cargos SET monto_original = 0, saldo = 0 WHERE id = :id",
        {"id": cargo_id},
    )
    common = {
        "id": uuid4(),
        "unidad_id": unidad_id,
        "condominio_id": condominio_id,
        "metodo_pago": "EFECTIVO",
        "referencia": None,
        "residente_nombre": "Prueba de constraint",
        "registrado_por": "OPERADOR_TEST",
        "fecha": date(2026, 10, 12),
        "exceso": 0,
    }
    assert_integrity_error(
        """INSERT INTO gc.pagos
        (id, unidad_id, condominio_id, monto, metodo_pago, referencia,
         residente_nombre, registrado_por, fecha, folio, exceso, estado)
        VALUES (:id, :unidad_id, :condominio_id, 0, :metodo_pago, :referencia,
         :residente_nombre, :registrado_por, :fecha, 'INVALIDO-MONTO', :exceso, 'VIGENTE')""",
        common,
    )
    with SqlAlchemyUnitOfWork(session_local) as uow:
        pago = RegistrarPagoUseCase(uow).ejecutar(
            RegistrarPagoCmd(
                unidad_id=unidad_id, monto=Decimal("1000"), metodo_pago="EFECTIVO",
                referencia=None, residente_nombre="Folio único", registrado_por="OPERADOR_TEST",
                fecha_pago=date(2026, 10, 12),
            )
        )
    duplicate = dict(common)
    duplicate["id"] = uuid4()
    duplicate["folio"] = pago.folio
    duplicate["monto"] = 1000
    assert_integrity_error(
        """INSERT INTO gc.pagos
        (id, unidad_id, condominio_id, monto, metodo_pago, referencia,
         residente_nombre, registrado_por, fecha, folio, exceso, estado)
        VALUES (:id, :unidad_id, :condominio_id, :monto, :metodo_pago, :referencia,
         :residente_nombre, :registrado_por, :fecha, :folio, :exceso, 'VIGENTE')""",
        duplicate,
    )
    assert_integrity_error(
        """INSERT INTO gc.comprobantes
        (folio, fecha_emision, unidad_id, residente_nombre, monto_pagado, metodo_pago,
         exceso, hash_sha256, datos_json)
        VALUES ('FOLIO-SIN-PAGO', DATE '2026-10-12', :unidad_id, 'Prueba FK',
         1000, 'EFECTIVO', 0, :hash, '{}'::jsonb)""",
        {"unidad_id": unidad_id, "hash": "a" * 64},
    )
\n