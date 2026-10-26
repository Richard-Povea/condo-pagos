from datetime import UTC, datetime
from uuid import UUID

from condo_pagos.domain.errors import DominioError, PagoYaAnuladoError
from condo_pagos.use_cases.ports import UnitOfWork


class AnularPagoUseCase:
    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    def ejecutar(self, pago_id: UUID, *, operador: str, motivo: str) -> None:
        with self.uow:
            # SQL directo: no cargar PagoModel antes del UPDATE compare-and-set.
            folio_existente = self.uow.pagos.obtener_folio_existente(pago_id)
            if folio_existente is None:
                raise DominioError(f"El pago {pago_id} no existe.")

            folio = self.uow.pagos.anular_si_vigente(
                pago_id,
                operador=operador.strip(),
                motivo=motivo.strip(),
                ahora=datetime.now(UTC),
            )
            if folio is None:
                raise PagoYaAnuladoError("El pago ya se encuentra anulado.")

            # Obtener el snapshot asociado solo después de ganar la anulación atómica.
            comprobante = self.uow.comprobantes.obtener_por_folio(folio)
            if not comprobante:
                raise DominioError(f"No se encontró el comprobante para el folio {folio}.")

            cargo_ids = [linea.cargo_id for linea in comprobante.lineas]
            cargos_bloqueados = self.uow.cargos.bloquear_para_actualizacion(cargo_ids)
            cargos_por_id = {cargo.id: cargo for cargo in cargos_bloqueados}

            for linea in comprobante.lineas:
                cargo = cargos_por_id.get(linea.cargo_id)
                if cargo is None:
                    raise DominioError(
                        f"No se encontró el cargo {linea.cargo_id} para revertir el pago."
                    )
                cargo.revertir(linea.monto_aplicado)
                self.uow.cargos.guardar(cargo)

            self.uow.commit()
