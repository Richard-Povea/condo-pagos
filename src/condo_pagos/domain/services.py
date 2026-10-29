from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from condo_pagos.domain.entities import Cargo, EstadoCargo
from condo_pagos.domain.errors import DominioError, PagoExcedeDeudaError
from condo_pagos.domain.money import cuantizar, parsear_monto


@dataclass(frozen=True)
class AplicacionDetalle:
    cargo_id: UUID
    monto_aplicado: Decimal


@dataclass(frozen=True)
class ResultadoDistribucion:
    monto_total_aplicado: Decimal
    exceso: Decimal
    aplicaciones: list[AplicacionDetalle]


def distribuir_pago(
    monto_pago: Decimal | int | str, 
    cargos_pendientes: Sequence[Cargo]
) -> ResultadoDistribucion:
    """Distribuye un pago entre los cargos pendientes aplicando la regla FIFO 
    (por vencimiento más antiguo y luego por id).
    Si el pago excede la deuda total, lanza PagoExcedeDeudaError.
    """
    monto_restante = parsear_monto(monto_pago)
    
    # Filtrar solo cargos que tengan saldo pendiente y no estén anulados
    validos = [c for c in cargos_pendientes if c.saldo > 0 and c.estado != EstadoCargo.ANULADO]
    
    # Ordenar por fecha de vencimiento ascendente y
    # como desempate por id (convertido a str/hex para orden determinista)
    cargos_ordenados = sorted(validos, key=lambda c: (c.vencimiento, str(c.id)))

    # Validar deuda total acumulada
    deuda_total = sum((c.saldo for c in cargos_ordenados), Decimal("0"))
    if monto_restante > deuda_total:
        exceso_calculado = monto_restante - deuda_total
        mensaje = "El pago ingresado ({}) excede la deuda total pendiente ({}) por {}."
        raise PagoExcedeDeudaError(
            mensaje.format(monto_restante, deuda_total, exceso_calculado)
        )

    aplicaciones: list[AplicacionDetalle] = []
    monto_original_procesado = monto_restante

    for cargo in cargos_ordenados:
        if monto_restante <= Decimal("0"):
            break

        a_pagar = min(monto_restante, cargo.saldo)
        # Aplicar directamente sobre el objeto cargo (mutación en memoria del dominio puro)
        cargo.aplicar(a_pagar)
        
        aplicaciones.append(
            AplicacionDetalle(
                cargo_id=cargo.id,
                monto_aplicado=a_pagar
            )
        )
        monto_restante -= a_pagar

    # Calculamos el exceso final (en este punto debería ser 0 porque validamos el total antes, 
    # pero mantenemos la robustez)
    exceso = cuantizar(monto_restante)
    total_aplicado = monto_original_procesado - exceso

    return ResultadoDistribucion(
        monto_total_aplicado=total_aplicado,
        exceso=exceso,
        aplicaciones=aplicaciones
    )

@dataclass(frozen=True)
class UnidadAlicuota:
    unidad_id: UUID
    alicuota: Decimal  # Ejemplo: Decimal("0.0525") para 5.25%


def prorratear(
    gasto_total: Decimal | int | str,
    unidades_alicuotas: Sequence[UnidadAlicuota]
) -> dict[UUID, Decimal]:
    """Calcula el prorrateo de gastos comunes por alícuota con cuantización entera (CLP).
    
    - Aplica ROUND_HALF_UP.
    - El residuo por redondeo se asigna a la unidad con mayor alícuota.
    - Valida que la suma de alícuotas sea exactamente 1 
    (con una tolerancia mínima de punto flotante).
    - Garantiza que la suma de los cargos resultante sea exactamente igual al gasto total.
    """
    total = parsear_monto(gasto_total)
    
    if not unidades_alicuotas:
        raise DominioError("Debe proporcionar al menos una unidad para prorratear.")

    # Validar que la suma de alícuotas sea igual a 1 (100%)
    suma_alicuotas = sum((ua.alicuota for ua in unidades_alicuotas), Decimal("0"))
    if abs(suma_alicuotas - Decimal("1.0")) > Decimal("0.000001"):
        mensaje = "La suma de las alícuotas de las unidades debe ser 1.0 (suma actual: {})."
        raise DominioError(mensaje.format(suma_alicuotas))

    resultados: dict[UUID, Decimal] = {}
    suma_parcial = Decimal("0")

    # Identificar la unidad con mayor alícuota para absorber el residuo de redondeo
    unidad_mayor = max(unidades_alicuotas, key=lambda ua: ua.alicuota)

    for ua in unidades_alicuotas:
        # El prorrateo bruto por unidad
        monto_bruto = total * ua.alicuota
        monto_cuantizado = cuantizar(monto_bruto)
        resultados[ua.unidad_id] = monto_cuantizado
        suma_parcial += monto_cuantizado

    # Calcular el residuo de redondeo y aplicarlo a la unidad con mayor alícuota
    residuo = total - suma_parcial
    if residuo != Decimal("0"):
        resultados[unidad_mayor.unidad_id] += residuo

    # Garantía matemática de cierre contable
    mensaje_error = "El prorrateo no cerró exacto con el total."
    if sum(resultados.values(), Decimal("0")) != total:
        raise DominioError(mensaje_error)

    return resultados