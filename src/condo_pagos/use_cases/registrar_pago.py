from uuid import uuid4

from condo_pagos.domain.comprobante import ComprobanteData, LineaCargo
from condo_pagos.domain.entities import EstadoPago, Pago
from condo_pagos.domain.errors import DominioError
from condo_pagos.domain.services import distribuir_pago
from condo_pagos.use_cases.dto import ComprobanteEmitido, RegistrarPagoCmd
from condo_pagos.use_cases.ports import UnitOfWork


class RegistrarPagoUseCase:
    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    def ejecutar(self, cmd: RegistrarPagoCmd) -> ComprobanteEmitido:
        with self.uow:
            # 1. Validar que la unidad exista y esté activa
            unidad = self.uow.unidades.obtener_por_id(cmd.unidad_id)
            if not unidad:
                raise DominioError(f"La unidad {cmd.unidad_id} no existe.")
            if not unidad.activa:
                raise DominioError(f"La unidad {unidad.codigo} se encuentra inactiva.")

            # 2. Validar referencia de pago duplicada
            if cmd.referencia and self.uow.pagos.existe_por_referencia(
                cmd.referencia, unidad.condominio_id, cmd.metodo_pago
            ):
                raise DominioError(
                    f"Ya existe un pago registrado con la referencia '{cmd.referencia}'."
                    )

            # 3. Obtener cargos pendientes de la unidad
            cargos_pendientes = self.uow.cargos.obtener_pendientes_por_unidad(cmd.unidad_id)
            if not cargos_pendientes:
                raise DominioError(f"La unidad {unidad.codigo} no registra cargos pendientes.")

            # Bloquear cargos para concurrencia
            cargo_ids = [c.id for c in cargos_pendientes]
            cargos_bloqueados = self.uow.cargos.bloquear_para_actualizacion(cargo_ids)

            # 4. Distribuir el pago usando FIFO
            resultado_distribucion = distribuir_pago(cmd.monto, cargos_bloqueados)

            # 5. Crear la entidad de Pago
            folio = self.uow.folios.siguiente_folio()
            pago_id = uuid4()
            pago = Pago(
                id=pago_id,
                unidad_id=cmd.unidad_id,
                monto=cmd.monto,
                metodo_pago=cmd.metodo_pago,
                referencia=cmd.referencia,
                residente_nombre=cmd.residente_nombre,
                fecha=cmd.fecha_pago,
                folio=folio,
                registrado_por=cmd.registrado_por,
                exceso=resultado_distribucion.exceso,
                estado=EstadoPago.VIGENTE,
            )
            self.uow.pagos.guardar(pago)

            # 6. Guardar los cambios en los cargos afectados
            lineas_comprobante: list[LineaCargo] = []
            for app in resultado_distribucion.aplicaciones:
                # Encontrar el cargo correspondiente bloqueado
                cargo_afectado = next(c for c in cargos_bloqueados if c.id == app.cargo_id)
                self.uow.cargos.guardar(cargo_afectado)

                lineas_comprobante.append(
                    LineaCargo(
                        cargo_id=cargo_afectado.id,
                        periodo=cargo_afectado.periodo,
                        monto_original=cargo_afectado.monto_original,
                        monto_aplicado=app.monto_aplicado,
                        saldo_restante=cargo_afectado.saldo,
                    )
                )

            # 7. Construir y guardar el ComprobanteData
            comprobante_data = ComprobanteData(
                folio=folio,
                fecha_emision=cmd.fecha_pago,
                unidad_id=cmd.unidad_id,
                residente_nombre=cmd.residente_nombre,
                monto_pagado=cmd.monto,
                metodo_pago=cmd.metodo_pago,
                lineas=tuple(lineas_comprobante),
                exceso=resultado_distribucion.exceso,
            )
            self.uow.comprobantes.guardar(comprobante_data, pdf_ruta=None)

            # 8. Confirmar transacción
            self.uow.commit()

            return ComprobanteEmitido(
                folio=folio,
                fecha_emision=cmd.fecha_pago,
                unidad_id=cmd.unidad_id,
                residente_nombre=cmd.residente_nombre,
                monto_pagado=cmd.monto,
                exceso=resultado_distribucion.exceso,
                pdf_ruta=None,
                hash_sha256=comprobante_data.hash_sha256(),
                lineas=tuple(lineas_comprobante),
            )