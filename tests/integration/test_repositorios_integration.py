from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import text

from condo_pagos.domain.entities import Cargo, EstadoCargo, EstadoPago, Pago
from condo_pagos.domain.errors import DominioError
from condo_pagos.infrastructure.database.bootstrap import verificar_esquema
from condo_pagos.infrastructure.database.engine import SessionLocal
from condo_pagos.infrastructure.database.unit_of_work import SqlAlchemyUnitOfWork


@pytest.fixture(scope="session", autouse=True)
def verificar_esquema_bd():
    """Verifica que el esquema esté listo antes de correr la suite de integración."""
    try:
        verificar_esquema()
    except Exception as e:
        pytest.skip(f"Base de datos no disponible para integración: {e}")


@pytest.fixture
def uow():
    uow_instance = SqlAlchemyUnitOfWork(SessionLocal)
    yield uow_instance
    # Limpieza o rollback por seguridad tras cada test
    uow_instance.session.rollback()
    uow_instance.session.close()


def test_integration_unidades_y_cargos(uow):
    unidad_id = uuid4()
    cargo_id = uuid4()
    
    with uow:
        # Insertar unidad directamente vía SQL o modelo para probar el repo
        uow.session.execute(
            text("""
            INSERT INTO gc.unidades (id, condominio_id, codigo, condominio_nombre, activa)
            VALUES (:id, :cond_id, :codigo, :nombre, :activa)
            ON CONFLICT (id) DO NOTHING
            """),
            {
                "id": str(unidad_id),
                "cond_id": str(uuid4()),
                "codigo": "202",
                "nombre": "Edificio Test",
                "activa": True
            }
        )
        uow.commit()

    with uow:
        # Probar lectura de unidad
        unidad_info = uow.unidades.obtener_por_id(unidad_id)
        assert unidad_info is not None
        assert unidad_info.codigo == "202"
        assert unidad_info.activa is True

        # Crear cargo pendiente
        cargo = Cargo(
            id=cargo_id,
            unidad_id=unidad_id,
            periodo="2026-11",
            monto_original=Decimal("40000"),
            saldo=Decimal("40000"),
            vencimiento=date(2026, 11, 10),
            estado=EstadoCargo.PENDIENTE
        )
        uow.cargos.guardar(cargo)
        uow.commit()

    with uow:
        # Obtener pendientes por unidad
        pendientes = uow.cargos.obtener_pendientes_por_unidad(unidad_id)
        assert len(pendientes) == 1
        assert pendientes[0].id == cargo_id
        assert pendientes[0].saldo == Decimal("40000")

        # Probar bloqueo FOR UPDATE
        bloqueados = uow.cargos.bloquear_para_actualizacion([cargo_id])
        assert len(bloqueados) == 1


def test_integration_folios_secuencia_y_pago_duplicado(uow):
    unidad_id = uuid4()
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
                "codigo": "303",
                "nombre": "Edificio Folios",
                "activa": True
            }
        )
        uow.commit()

    with uow:
        # Generar folio atómico
        folio1 = uow.folios.siguiente_folio()
        folio2 = uow.folios.siguiente_folio()
        assert folio1 != folio2
        assert folio1.startswith("2026")

        # Registrar pago
        pago = Pago(
            id=uuid4(),
            unidad_id=unidad_id,
            monto=Decimal("15000"),
            metodo_pago="TRANSFERENCIA",
            referencia="REF-INTEGRATION-001",
            residente_nombre="Carlos Soto",
            fecha=date(2026, 10, 12),
            folio=folio1,
            exceso=Decimal("0"),
            estado=EstadoPago.VIGENTE
        )
        uow.pagos.guardar(pago)
        uow.commit()

    # Probar unicidad de referencia (traducción a DominioError)
    with uow:
        pago_duplicado = Pago(
            id=uuid4(),
            unidad_id=unidad_id,
            monto=Decimal("15000"),
            metodo_pago="EFECTIVO",
            referencia="REF-INTEGRATION-001", # Misma referencia
            residente_nombre="Otro Residente",
            fecha=date(2026, 10, 12),
            folio=folio2,
            exceso=Decimal("0"),
            estado=EstadoPago.VIGENTE
        )
        uow.pagos.guardar(pago_duplicado)
        
        with pytest.raises(DominioError, match="Ya existe un pago registrado con esa referencia"):
            uow.commit()