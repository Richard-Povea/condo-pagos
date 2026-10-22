from uuid import UUID

from condo_pagos.domain.entities import EstadoCargo, EstadoPago
from condo_pagos.domain.errors import DominioError
from condo_pagos.use_cases.ports import UnitOfWork


class AnularPagoUseCase:
    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    def ejecutar(self, pago_id: UUID, *, operador: str, motivo: str) -> None:
        with self.uow:
            # 1. Obtener el pago
            pago = self.uow.pagos.obtener_por_id(pago_id)
            if not pago:
                raise DominioError(f"El pago {pago_id} no existe.")
            if pago.estado == EstadoPago.ANULADO:
                raise DominioError("El pago ya se encuentra anulado.")

            # 2. Obtener el comprobante asociado para conocer qué cargos fueron afectados
            comprobante = self.uow.comprobantes.obtener_por_folio(pago.folio)
            if not comprobante:
                raise DominioError(f"No se encontró el comprobante para el folio {pago.folio}.")

            # 3. Bloquear los cargos afectados para actualización concurrente segura
            cargo_ids = [linea.cargo_id for linea in comprobante.lineas]
            cargos_bloqueados = self.uow.cargos.bloquear_para_actualizacion(cargo_ids)

            # 4. Restaurar los saldos de los cargos
            for linea in comprobante.lineas:
                cargo = next((c for c in cargos_bloqueados if c.id == linea.cargo_id), None)
                if cargo:
                    # El nuevo saldo vuelve a sumar lo que se le había aplicado
                    cargo.saldo += linea.monto_aplicado
                    if cargo.saldo > 0:
                        cargo.estado = EstadoCargo.PENDIENTE
                    self.uow.cargos.guardar(cargo)

            # 5. Registrar estado y auditoría requeridos por la restricción SQL.
            pago.anular(operador=operador, motivo=motivo)
            self.uow.pagos.guardar(pago)

            self.uow.commit()