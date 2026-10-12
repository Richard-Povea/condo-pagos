from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from hypothesis import given
from hypothesis import strategies as st

from condo_pagos.domain.comprobante import ComprobanteData, LineaCargo
from condo_pagos.domain.entities import Cargo, EstadoCargo
from condo_pagos.domain.errors import (
    DominioError,
    MontoInvalidoError,
    PagoExcedeDeudaError,
)
from condo_pagos.domain.money import parsear_monto
from condo_pagos.domain.services import (
    UnidadAlicuota,
    distribuir_pago,
    prorratear,
)


def test_parsear_monto_valido():
    assert parsear_monto("125.000") == Decimal("125000")
    assert parsear_monto(50000) == Decimal("50000")
    assert parsear_monto(Decimal("1000")) == Decimal("1000")


def test_parsear_monto_invalido():
    with pytest.raises(MontoInvalidoError):
        parsear_monto("125.000,50")  # Con decimales (Chile no usa)
    with pytest.raises(MontoInvalidoError):
        parsear_monto(125.50)  # type: ignore # Float prohibido
    with pytest.raises(MontoInvalidoError):
        parsear_monto("-1000")  # Negativo
    with pytest.raises(MontoInvalidoError):
        parsear_monto("")  # Vacío


def test_cargo_aplicar_y_revertir():
    cargo = Cargo(
        id=uuid4(),
        unidad_id=uuid4(),
        periodo="2026-10",
        monto_original=Decimal("100000"),
        saldo=Decimal("100000"),
        vencimiento=date(2026, 10, 10),
    )

    # Pago parcial
    exceso = cargo.aplicar(Decimal("40000"))
    assert exceso == Decimal("0")
    assert cargo.saldo == Decimal("60000")
    assert cargo.estado == EstadoCargo.PENDIENTE

    # Pago total con exceso
    exceso = cargo.aplicar(Decimal("70000"))
    assert exceso == Decimal("10000")
    assert cargo.saldo == Decimal("0")
    assert cargo.estado == EstadoCargo.PAGADO

    # Revertir parte del pago
    cargo.revertir(Decimal("30000"))
    assert cargo.saldo == Decimal("30000")
    assert cargo.estado == EstadoCargo.PENDIENTE


def test_distribuir_pago_fifo():
    c1 = Cargo(
        id=uuid4(), unidad_id=uuid4(), periodo="2026-08",
        monto_original=Decimal("50000"), saldo=Decimal("50000"),
        vencimiento=date(2026, 8, 10)
    )
    c2 = Cargo(
        id=uuid4(), unidad_id=uuid4(), periodo="2026-09",
        monto_original=Decimal("50000"), saldo=Decimal("50000"),
        vencimiento=date(2026, 9, 10)
    )

    # Pagar exactamente el cargo más antiguo (c1)
    resultado = distribuir_pago(Decimal("50000"), [c2, c1]) # desordenados intencionalmente
    assert resultado.monto_total_aplicado == Decimal("50000")
    assert resultado.exceso == Decimal("0")
    assert len(resultado.aplicaciones) == 1
    assert resultado.aplicaciones[0].cargo_id == c1.id
    assert c1.saldo == Decimal("0")
    assert c2.saldo == Decimal("50000")


def test_distribuir_pago_excede_deuda():
    c1 = Cargo(
        id=uuid4(), unidad_id=uuid4(), periodo="2026-10",
        monto_original=Decimal("50000"), saldo=Decimal("50000"),
        vencimiento=date(2026, 10, 10)
    )
    with pytest.raises(PagoExcedeDeudaError):
        distribuir_pago(Decimal("60000"), [c1])


def test_prorratear_exacto():
    u1, u2, u3 = uuid4(), uuid4(), uuid4()
    alicuotas = [
        UnidadAlicuota(unidad_id=u1, alicuota=Decimal("0.5")),
        UnidadAlicuota(unidad_id=u2, alicuota=Decimal("0.3")),
        UnidadAlicuota(unidad_id=u3, alicuota=Decimal("0.2")),
    ]
    gasto = Decimal("100000")
    resultado = prorratear(gasto, alicuotas)
    
    assert resultado[u1] == Decimal("50000")
    assert resultado[u2] == Decimal("30000")
    assert resultado[u3] == Decimal("20000")
    assert sum(resultado.values()) == gasto


def test_comprobante_data_ciclo_json_y_hash():
    linea = LineaCargo(
        cargo_id=uuid4(),
        periodo="2026-10",
        monto_original=Decimal("100000"),
        monto_aplicado=Decimal("100000"),
        saldo_restante=Decimal("0"),
    )
    comp = ComprobanteData(
        folio="COMP-001",
        fecha_emision=date(2026, 10, 11),
        unidad_id=uuid4(),
        residente_nombre="Juan Pérez",
        monto_pagado=Decimal("100000"),
        metodo_pago="TRANSFERENCIA",
        lineas=(linea,),
        exceso=Decimal("0"),
        hash_anterior=None,
    )

    json_str = comp.a_json()
    comp_reconstruido = ComprobanteData.desde_json(json_str)

    assert comp == comp_reconstruido
    assert comp.hash_sha256() == comp_reconstruido.hash_sha256()

def test_cargo_errores_estado_y_montos():
    cargo = Cargo(
        id=uuid4(), unidad_id=uuid4(), periodo="2026-10",
        monto_original=Decimal("50000"), saldo=Decimal("50000"),
        vencimiento=date(2026, 10, 10),
        estado=EstadoCargo.ANULADO
    )
    # Intentar aplicar pago a cargo anulado
    with pytest.raises(DominioError, match="anulado"):
        cargo.aplicar(Decimal("10000"))

    # Intentar aplicar pago menor o igual a cero
    cargo_pendiente = Cargo(
        id=uuid4(), unidad_id=uuid4(), periodo="2026-10",
        monto_original=Decimal("50000"), saldo=Decimal("50000"),
        vencimiento=date(2026, 10, 10)
    )
    with pytest.raises(MontoInvalidoError):
        cargo_pendiente.aplicar(Decimal("0"))

    # Intentar aplicar a cargo ya pagado
    cargo_pendiente.aplicar(Decimal("50000"))
    with pytest.raises(DominioError, match="pagado"):
        cargo_pendiente.aplicar(Decimal("10000"))

    # Revertir con monto inválido o exceso sobre original
    with pytest.raises(MontoInvalidoError):
        cargo_pendiente.revertir(Decimal("-5000"))
    
    with pytest.raises(DominioError, match="superar el monto original"):
        cargo_pendiente.revertir(Decimal("60000"))

def test_money_casos_borde():
    # Tipo de dato no soportado
    with pytest.raises(MontoInvalidoError):
        parsear_monto([123])  # type: ignore

    # Formato con coma (inválido para pesos chilenos)
    with pytest.raises(MontoInvalidoError, match="decimales"):
        parsear_monto("100.000,50")


def test_prorratear_casos_borde():
    # Lista vacía de alícuotas
    with pytest.raises(DominioError, match="al menos una unidad"):
        prorratear(Decimal("100000"), [])

    # Suma de alícuotas distinta de 1.0
    u1 = uuid4()
    with pytest.raises(DominioError, match="debe ser 1.0"):
        prorratear(Decimal("100000"), [UnidadAlicuota(unidad_id=u1, alicuota=Decimal("0.5"))])


# --- Pruebas de propiedad con Hypothesis ---

@given(
    monto_pago=st.decimals(min_value=1, max_value=500000, places=0),
    saldo_cargo=st.decimals(min_value=100000, max_value=1000000, places=0)
)
def test_property_distribucion_suma_y_exceso(monto_pago, saldo_cargo):
    c1 = Cargo(
        id=uuid4(), unidad_id=uuid4(), periodo="2026-10",
        monto_original=saldo_cargo, saldo=saldo_cargo,
        vencimiento=date(2026, 10, 10)
    )
    
    if monto_pago > saldo_cargo:
        with pytest.raises(PagoExcedeDeudaError):
            distribuir_pago(monto_pago, [c1])
    else:
        res = distribuir_pago(monto_pago, [c1])
        assert res.monto_total_aplicado + res.exceso == monto_pago
        assert c1.saldo == saldo_cargo - monto_pago