from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from condo_pagos.domain.entities import Cargo, EstadoCargo
from condo_pagos.domain.errors import DominioError
from condo_pagos.infrastructure.database.bootstrap import ESQUEMA_VERSION_ESPERADA
from condo_pagos.infrastructure.database.engine import SessionLocal
from condo_pagos.infrastructure.database.unit_of_work import SqlAlchemyUnitOfWork
from condo_pagos.use_cases.anular_pago import AnularPagoUseCase
from condo_pagos.use_cases.dto import RegistrarPagoCmd
from condo_pagos.use_cases.registrar_pago import RegistrarPagoUseCase

pytestmark = pytest.mark.integration


@pytest.fixture
def uow():
    uow_instance = SqlAlchemyUnitOfWork(SessionLocal)
    with uow_instance:
        # Limpiar todas las tablas incluyendo folios_secuencia y reiniciar contadores
        uow_instance.session.execute(
            text("TRUNCATE TABLE gc.comprobantes, gc.pagos, gc.cargos, gc.unidades, gc.folios_secuencia RESTART IDENTITY CASCADE")
        )
        uow_instance.commit()
    
    yield uow_instance
    

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
                "activa": True
            }
        )
        cargo = Cargo(
            id=cargo_id,
            unidad_id=unidad_id,
            periodo="2026-10",
            monto_original=monto,
            saldo=monto,
            vencimiento=date(2026, 10, 10),
            estado=EstadoCargo.PENDIENTE
        )
        uow.cargos.guardar(cargo)
        uow.commit()


def test_1_folios_concurrentes(uow):  # <-- Asegúrate de recibir la uow del fixture aquí
    """6 hilos pagando en distintas unidades producen folios [1..6] sin huecos ni duplicados."""
    unidades = [uuid4() for _ in range(6)]
    cargos = [uuid4() for _ in range(6)]
    
    # Preparar todas las unidades y cargos de forma síncrona y limpia
    for i in range(6):
        with SqlAlchemyUnitOfWork(SessionLocal) as uow_prep:
            _crear_unidad_y_cargo(uow_prep, unidades[i], cargos[i], codigo=str(200 + i))

    def realizar_pago(idx):
        # Cada hilo abre su propia UoW independiente
        with SqlAlchemyUnitOfWork(SessionLocal) as uow_hilo:
            caso_uso = RegistrarPagoUseCase(uow_hilo)
            cmd = RegistrarPagoCmd(
                unidad_id=unidades[idx],
                monto=Decimal("50000"),
                metodo_pago="TRANSFERENCIA",
                referencia=f"REF-CONC-{idx}",
                residente_nombre=f"Residente {idx}",
                fecha_pago=date(2026, 10, 12)
            )
            return caso_uso.ejecutar(cmd).folio

    folios_obtenidos = []
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = [executor.submit(realizar_pago, i) for i in range(6)]
        for future in as_completed(futures):
            folios_obtenidos.append(future.result())

    anio_actual = str(date.today().year)
    numeros = sorted([int(f.split("-")[1]) for f in folios_obtenidos])
    assert numeros == [1, 2, 3, 4, 5, 6]
    for f in folios_obtenidos:
        assert f.startswith(anio_actual)


def test_2_doble_pago_simultaneo_misma_unidad():
    """Doble pago simultáneo en la misma unidad: el segundo falla porque FOR UPDATE serializa."""
    unidad_id = uuid4()
    cargo_id = uuid4()
    uow_prep = SqlAlchemyUnitOfWork(SessionLocal)
    _crear_unidad_y_cargo(uow_prep, unidad_id, cargo_id, monto=Decimal("50000"), codigo="301")

    def intentar_pago(ref):
        uow = SqlAlchemyUnitOfWork(SessionLocal)
        caso_uso = RegistrarPagoUseCase(uow)
        cmd = RegistrarPagoCmd(
            unidad_id=unidad_id,
            monto=Decimal("50000"),
            metodo_pago="TRANSFERENCIA",
            referencia=ref,
            residente_nombre="Simultáneo",
            fecha_pago=date(2026, 10, 12)
        )
        return caso_uso.ejecutar(cmd)

    exitos = 0
    errores = 0
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(intentar_pago, "REF-SIM-A"),
            executor.submit(intentar_pago, "REF-SIM-B")
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
        fecha_pago=date(2026, 10, 12)
    )
    caso_uso = RegistrarPagoUseCase(uow)
    caso_uso.ejecutar(cmd)

    # Segundo intento con misma referencia
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
        fecha_pago=date(2026, 10, 12)
    )
    resultado = caso_uso.ejecutar(cmd)

    # Intentar hacer UPDATE directo sobre la tabla comprobantes
    with pytest.raises(Exception, match="inmutables"):
        uow.session.execute(
            text("UPDATE gc.comprobantes SET residente_nombre = 'Modificado' WHERE folio = :folio"),
            {"folio": resultado.folio}
        )
        uow.commit()


def test_6_constraints_check_y_fk(uow):
    """Verificar violaciones de integridad referencial (FK)."""
    with uow:
        with pytest.raises(IntegrityError):
            uow.session.execute(
                text("""
                    INSERT INTO gc.cargos (id, unidad_id, periodo, monto_original, saldo, vencimiento, estado)
                    VALUES (:id, :unidad_id, '2026-10', 1000, 1000, '2026-10-10', 'PENDIENTE')
                """),
                {"id": str(uuid4()), "unidad_id": str(uuid4())}  # Unidad inexistente
            )
            uow.commit()


def test_7_anulacion_restaura_saldos(uow):
    """La anulación restaura los saldos de los cargos y el folio sigue ocupado."""
    unidad_id = uuid4()
    cargo_id = uuid4()
    _crear_unidad_y_cargo(uow, unidad_id, cargo_id, monto=Decimal("50000"), codigo="701")

    # Al inicio, el cargo está pendiente (hay 1 pendiente)
    pendientes_iniciales = uow.cargos.obtener_pendientes_por_unidad(unidad_id)
    assert len(pendientes_iniciales) == 1

    caso_uso_pago = RegistrarPagoUseCase(uow)
    cmd = RegistrarPagoCmd(
        unidad_id=unidad_id,
        monto=Decimal("50000"),
        metodo_pago="TRANSFERENCIA",
        referencia="REF-ANULAR-01",
        residente_nombre="Anular Test",
        fecha_pago=date(2026, 10, 12)
    )
    _ = caso_uso_pago.ejecutar(cmd)

    # Después del pago, ya no quedan cargos pendientes (longitud 0)
    pendientes_antes_anular = uow.cargos.obtener_pendientes_por_unidad(unidad_id)
    assert len(pendientes_antes_anular) == 0

    # Obtener el ID del pago registrado
    pago_db = uow.session.execute(
        text("SELECT id FROM gc.pagos WHERE referencia = 'REF-ANULAR-01'")
    ).fetchone()

    # Anular pago
    caso_uso_anular = AnularPagoUseCase(uow)
    caso_uso_anular.ejecutar(pago_db.id)

    # Verificar que tras la anulación el saldo del cargo volvió a 50000 y aparece como pendiente
    pendientes_despues = uow.cargos.obtener_pendientes_por_unidad(unidad_id)
    assert len(pendientes_despues) == 1
    assert pendientes_despues[0].saldo == Decimal("50000")


def test_8_esquema_desde_cero():
    """En una BD vacía, verificar versión de schema_info."""
    with SessionLocal() as session:
        version = session.execute(text("SELECT version FROM gc.schema_info")).scalar_one()
        assert version == ESQUEMA_VERSION_ESPERADA