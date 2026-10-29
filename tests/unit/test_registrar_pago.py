from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from condo_pagos.domain.entities import Cargo, EstadoCargo
from condo_pagos.domain.errors import DominioError
from condo_pagos.use_cases.dto import RegistrarPagoCmd, UnidadInfo
from condo_pagos.use_cases.registrar_pago import RegistrarPagoUseCase
from tests.fakes.fake_uow import FakeUnitOfWork


@pytest.fixture
def py_fixture_uow() -> FakeUnitOfWork:
    unidad_id = uuid4()
    cargo_id = uuid4()
    
    unidades = {
        unidad_id: UnidadInfo(
            id=unidad_id,
            condominio_id=uuid4(),
            codigo="101",
            condominio_nombre="Condominio Los Alerces",
            activa=True
        )
    }
    cargos = {
        cargo_id: Cargo(
            id=cargo_id,
            unidad_id=unidad_id,
            periodo="2026-10",
            monto_original=Decimal("50000"),
            saldo=Decimal("50000"),
            vencimiento=date(2026, 10, 10),
            estado=EstadoCargo.PENDIENTE
        )
    }
    return FakeUnitOfWork(
        unidades_iniciales=unidades,
        cargos_iniciales=cargos,
        contador_folio=1
    )


def test_registrar_pago_camino_feliz(py_fixture_uow):
    uow = py_fixture_uow
    unidad_id = list(uow._unidades_store.keys())[0]

    cmd = RegistrarPagoCmd(
        unidad_id=unidad_id,
        monto=Decimal("50000"),
        metodo_pago="TRANSFERENCIA",
        referencia="REF-12345",
        residente_nombre="María González",
        registrado_por="OPERADOR_TEST",
        fecha_pago=date(2026, 10, 12)
    )

    caso_uso = RegistrarPagoUseCase(uow)
    resultado = caso_uso.ejecutar(cmd)

    # Verificaciones del resultado y folio
    assert resultado.folio == "2026-000001"
    assert resultado.monto_pagado == Decimal("50000")
    assert resultado.exceso == Decimal("0")
    assert len(resultado.lineas) == 1
    assert resultado.lineas[0].saldo_restante == Decimal("0")

    # Verificar que el pago quedó guardado en el repo
    pagos = list(uow._pagos_store.values())
    assert len(pagos) == 1
    assert pagos[0].referencia == "REF-12345"
    assert pagos[0].folio == "2026-000001"
    assert pagos[0].registrado_por == "OPERADOR_TEST"


def test_registrar_pago_exceso_deuda_no_consume_folio(py_fixture_uow):
    uow = py_fixture_uow
    unidad_id = list(uow._unidades_store.keys())[0]

    cmd = RegistrarPagoCmd(
        unidad_id=unidad_id,
        monto=Decimal("60000"),  # Supera los 50000 del cargo
        metodo_pago="TRANSFERENCIA",
        referencia="REF-99999",
        residente_nombre="Pedro Picapiedra",
        registrado_por="OPERADOR_TEST",
        fecha_pago=date(2026, 10, 12)
    )

    caso_uso = RegistrarPagoUseCase(uow)
    
    with pytest.raises(DominioError):
        caso_uso.ejecutar(cmd)

    # Verificar que el folio NO se incrementó (rollback del contador o no commit)
    assert uow.folios.siguiente_folio() == "2026-000001"
    # Verificar que no se guardó ningún pago
    assert len(uow._pagos_store) == 0


def test_registrar_pago_rollback_por_fallo_externo(py_fixture_uow):
    uow = py_fixture_uow
    unidad_id = list(uow._unidades_store.keys())[0]

    cmd = RegistrarPagoCmd(
        unidad_id=unidad_id,
        monto=Decimal("50000"),
        metodo_pago="TRANSFERENCIA",
        referencia="REF-777",
        residente_nombre="Test Fallo",
        registrado_por="OPERADOR_TEST",
        fecha_pago=date(2026, 10, 12)
    )

    # Forzamos un fallo simulando una excepción al guardar el comprobante
    def guardar_con_fallo(*args, **kwargs):
        raise RuntimeError("Fallo de disco o red simulado")
    uow.comprobantes.guardar = guardar_con_fallo

    caso_uso = RegistrarPagoUseCase(uow)
    with pytest.raises(RuntimeError, match="Fallo de disco"):
        caso_uso.ejecutar(cmd)

    # El UoW debió hacer rollback: el pago no debe existir
    # El saldo del cargo debe mantenerse intacto
    assert len(uow._pagos_store) == 0
    cargo_actual = list(uow._cargos_store.values())[0]
    assert cargo_actual.saldo == Decimal("50000")
    assert uow.folios.siguiente_folio() == "2026-000001"


def test_registrar_pago_unidad_inactiva(py_fixture_uow):
    uow = py_fixture_uow
    unidad_id = list(uow._unidades_store.keys())[0]
    
    # Marcar unidad como inactiva
    info_actual = uow._unidades_store[unidad_id]
    uow._unidades_store[unidad_id] = UnidadInfo(
        id=info_actual.id,
        condominio_id=info_actual.condominio_id,
        codigo=info_actual.codigo,
        condominio_nombre=info_actual.condominio_nombre,
        activa=False
    )

    cmd = RegistrarPagoCmd(
        unidad_id=unidad_id,
        monto=Decimal("50000"),
        metodo_pago="EFECTIVO",
        referencia="REF-001",
        residente_nombre="Inactivo",
        registrado_por="OPERADOR_TEST",
        fecha_pago=date(2026, 10, 12)
    )

    caso_uso = RegistrarPagoUseCase(uow)
    with pytest.raises(DominioError, match="inactiva"):
        caso_uso.ejecutar(cmd)


def test_registrar_pago_unidad_sin_deuda(py_fixture_uow):
    uow = py_fixture_uow
    unidad_id = list(uow._unidades_store.keys())[0]
    
    # Vaciar cargos pendientes
    uow._cargos_store.clear()

    cmd = RegistrarPagoCmd(
        unidad_id=unidad_id,
        monto=Decimal("10000"),
        metodo_pago="EFECTIVO",
        referencia="REF-002",
        residente_nombre="Sin Deuda",
        registrado_por="OPERADOR_TEST",
        fecha_pago=date(2026, 10, 12)
    )

    caso_uso = RegistrarPagoUseCase(uow)
    with pytest.raises(DominioError, match="no registra cargos pendientes"):
        caso_uso.ejecutar(cmd)


def test_registrar_pago_referencia_duplicada(py_fixture_uow):
    uow = py_fixture_uow
    unidad_id = list(uow._unidades_store.keys())[0]

    cmd = RegistrarPagoCmd(
        unidad_id=unidad_id,
        monto=Decimal("50000"),
        metodo_pago="TRANSFERENCIA",
        referencia="REF-DUP",
        residente_nombre="Duplicado",
        registrado_por="OPERADOR_TEST",
        fecha_pago=date(2026, 10, 12)
    )

    caso_uso = RegistrarPagoUseCase(uow)
    # Primer registro exitoso
    caso_uso.ejecutar(cmd)

    # Segundo registro con la misma referencia debe fallar
    with pytest.raises(DominioError, match="Ya existe un pago registrado"):
        caso_uso.ejecutar(cmd)

def test_transferencia_requiere_referencia(py_fixture_uow):
    uow = py_fixture_uow
    unidad_id = list(uow._unidades_store.keys())[0]
    cmd = RegistrarPagoCmd(
        unidad_id=unidad_id,
        monto=Decimal("10000"),
        metodo_pago="TRANSFERENCIA",
        referencia="   ",
        residente_nombre="Residente de prueba",
        registrado_por="OPERADOR_TEST",
        fecha_pago=date(2026, 10, 12),
    )

    with pytest.raises(DominioError, match="transferencia debe tener una referencia"):
        RegistrarPagoUseCase(uow).ejecutar(cmd)

    assert len(uow._pagos_store) == 0


def test_tarjeta_no_esta_habilitada(py_fixture_uow):
    uow = py_fixture_uow
    unidad_id = list(uow._unidades_store.keys())[0]
    cmd = RegistrarPagoCmd(
        unidad_id=unidad_id,
        monto=Decimal("10000"),
        metodo_pago="TARJETA",
        referencia=None,
        residente_nombre="Residente de prueba",
        registrado_por="OPERADOR_TEST",
        fecha_pago=date(2026, 10, 12),
    )

    with pytest.raises(DominioError) as exc:
        RegistrarPagoUseCase(uow).ejecutar(cmd)

    assert str(exc.value) == "Este método de pago aún no está habilitado."
    assert len(uow._pagos_store) == 0


def test_metodo_desconocido_mensaje_exacto(py_fixture_uow):
    uow = py_fixture_uow
    unidad_id = list(uow._unidades_store.keys())[0]
    cmd = RegistrarPagoCmd(
        unidad_id=unidad_id,
        monto=Decimal("10000"),
        metodo_pago="CHEQUE",
        referencia=None,
        residente_nombre="Residente de prueba",
        registrado_por="OPERADOR_TEST",
        fecha_pago=date(2026, 10, 12),
    )

    with pytest.raises(DominioError) as exc:
        RegistrarPagoUseCase(uow).ejecutar(cmd)

    assert str(exc.value) == "Método de pago no reconocido."
    assert len(uow._pagos_store) == 0


def test_tarjeta_con_espacios_y_minusculas_sigue_no_habilitada(py_fixture_uow):
    uow = py_fixture_uow
    unidad_id = list(uow._unidades_store.keys())[0]
    cmd = RegistrarPagoCmd(
        unidad_id=unidad_id,
        monto=Decimal("10000"),
        metodo_pago=" tarjeta ",
        referencia=None,
        residente_nombre="Residente de prueba",
        registrado_por="OPERADOR_TEST",
        fecha_pago=date(2026, 10, 12),
    )

    with pytest.raises(DominioError) as exc:
        RegistrarPagoUseCase(uow).ejecutar(cmd)

    assert str(exc.value) == "Este método de pago aún no está habilitado."
    assert len(uow._pagos_store) == 0


def test_normaliza_metodo_y_referencia_de_pago(py_fixture_uow):
    uow = py_fixture_uow
    unidad_id = list(uow._unidades_store.keys())[0]
    cmd = RegistrarPagoCmd(
        unidad_id=unidad_id,
        monto=Decimal("10000"),
        metodo_pago=" transferencia ",
        referencia="  REF-ESPACIOS  ",
        residente_nombre="Residente de prueba",
        registrado_por="OPERADOR_TEST",
        fecha_pago=date(2026, 10, 12),
    )

    RegistrarPagoUseCase(uow).ejecutar(cmd)

    pago = next(iter(uow._pagos_store.values()))
    assert pago.metodo_pago == "TRANSFERENCIA"
    assert pago.referencia == "REF-ESPACIOS"

