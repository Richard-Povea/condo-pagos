from copy import deepcopy
from datetime import datetime
from uuid import UUID

from condo_pagos.domain.comprobante import ComprobanteData
from condo_pagos.domain.entities import Cargo, EstadoPago, Pago
from condo_pagos.use_cases.dto import UnidadInfo
from condo_pagos.use_cases.ports import (
    CargosRepository,
    ComprobantesRepository,
    FoliosRepository,
    PagosRepository,
    UnidadesRepository,
    UnitOfWork,
)


class FakeUnidadesRepository(UnidadesRepository):
    def __init__(self, unidades: dict[UUID, UnidadInfo]) -> None:
        self._unidades = unidades

    def obtener_por_id(self, unidad_id: UUID) -> UnidadInfo | None:
        return self._unidades.get(unidad_id)


class FakeCargosRepository(CargosRepository):
    def __init__(self, cargos: dict[UUID, Cargo]) -> None:
        self._cargos = cargos

    def obtener_pendientes_por_unidad(self, unidad_id: UUID) -> list[Cargo]:
        return [
            cargo for cargo in self._cargos.values()
            if cargo.unidad_id == unidad_id and cargo.esta_pendiente()
        ]

    def guardar(self, cargo: Cargo) -> None:
        self._cargos[cargo.id] = cargo

    def bloquear_para_actualizacion(self, cargo_ids: list[UUID]) -> list[Cargo]:
        return [self._cargos[cid] for cid in cargo_ids if cid in self._cargos]


class FakePagosRepository(PagosRepository):
    def __init__(
        self, pagos: dict[UUID, Pago], condominios_por_unidad: dict[UUID, UUID]
    ) -> None:
        self._pagos = pagos
        self._condominios_por_unidad = condominios_por_unidad

    def guardar(self, pago: Pago) -> None:
        condominio_id = self._condominios_por_unidad.get(pago.unidad_id)
        if condominio_id is not None:
            pago._establecer_condominio_id(condominio_id)
        self._pagos[pago.id] = pago

    def obtener_por_id(self, pago_id: UUID) -> Pago | None:
        return self._pagos.get(pago_id)

    def obtener_folio_existente(self, pago_id: UUID) -> str | None:
        pago = self._pagos.get(pago_id)
        return pago.folio if pago is not None else None

    def anular_si_vigente(
        self, pago_id: UUID, *, operador: str, motivo: str, ahora: datetime
    ) -> str | None:
        pago = self._pagos.get(pago_id)
        if pago is None or pago.estado != EstadoPago.VIGENTE:
            return None
        pago.estado = EstadoPago.ANULADO
        pago.anulado_en = ahora
        pago.anulado_por = operador
        pago.motivo_anulacion = motivo
        return pago.folio

    def existe_por_referencia(
        self, referencia: str | None, condominio_id: UUID, metodo_pago: str
    ) -> bool:
        return any(
            p.referencia == referencia
            and p.estado == EstadoPago.VIGENTE
            and p.condominio_id == condominio_id
            and p.metodo_pago == metodo_pago
            for p in self._pagos.values()
        )

    def listar_recientes_por_unidad(self, unidad_id: UUID, limite: int = 10) -> list[Pago]:
        filtrados = [p for p in self._pagos.values() if p.unidad_id == unidad_id]
        ordenados = sorted(filtrados, key=lambda x: x.fecha, reverse=True)
        return ordenados[:limite]


class FakeFoliosRepository(FoliosRepository):
    def __init__(self, contador: int = 1, anio: str = "2026") -> None:
        self._contador = contador
        self._anio = anio

    def siguiente_folio(self) -> str:
        folio_str = f"{self._anio}-{self._contador:06d}"
        self._contador += 1
        return folio_str

    def obtener_estado(self) -> int:
        return self._contador

    def restaurar_estado(self, contador: int) -> None:
        self._contador = contador


class FakeComprobantesRepository(ComprobantesRepository):
    def __init__(self) -> None:
        self._comprobantes: dict[str, tuple[ComprobanteData, str | None]] = {}

    def guardar(self, comprobante: ComprobanteData, pdf_ruta: str | None) -> None:
        self._comprobantes[comprobante.folio] = (comprobante, pdf_ruta)

    def obtener_por_folio(self, folio: str) -> ComprobanteData | None:
        data = self._comprobantes.get(folio)
        return data[0] if data else None

    def actualizar_ruta_pdf(self, folio: str, pdf_ruta: str) -> None:
        if folio in self._comprobantes:
            comp, _ = self._comprobantes[folio]
            self._comprobantes[folio] = (comp, pdf_ruta)

    def obtener_estado(self) -> dict[str, tuple[ComprobanteData, str | None]]:
        return self._comprobantes

    def restaurar_estado(self, estado: dict[str, tuple[ComprobanteData, str | None]]) -> None:
        self._comprobantes.clear()
        self._comprobantes.update(estado)


class FakeUnitOfWork(UnitOfWork):
    """Implementación in-memory transaccional del UnitOfWork para pruebas."""

    def __init__(
        self,
        unidades_iniciales: dict[UUID, UnidadInfo] | None = None,
        cargos_iniciales: dict[UUID, Cargo] | None = None,
        pagos_iniciales: dict[UUID, Pago] | None = None,
        contador_folio: int = 1,
    ) -> None:
        self._unidades_store = unidades_iniciales or {}
        self._cargos_store = cargos_iniciales or {}
        self._pagos_store = pagos_iniciales or {}

        # Referencias concretas, solo para uso interno del fake
        self._folios_fake = FakeFoliosRepository(contador=contador_folio)
        self._comprobantes_fake = FakeComprobantesRepository()

        # Atributos del puerto, con el tipo abstracto declarado en la base
        self.unidades = FakeUnidadesRepository(self._unidades_store)
        self.cargos = FakeCargosRepository(self._cargos_store)
        condominios_por_unidad = {
            unidad.id: unidad.condominio_id for unidad in self._unidades_store.values()
        }
        self.pagos = FakePagosRepository(self._pagos_store, condominios_por_unidad)
        self.folios = self._folios_fake
        self.comprobantes = self._comprobantes_fake

        self._committed = False
        self._snapshot: dict = {}

    def __enter__(self) -> "FakeUnitOfWork":
        self._committed = False
        self._snapshot = {
            "unidades": deepcopy(self._unidades_store),
            "cargos": deepcopy(self._cargos_store),
            "pagos": deepcopy(self._pagos_store),
            "contador_folio": self._folios_fake._contador,
            "comprobantes": deepcopy(self._comprobantes_fake._comprobantes),
        }
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        if exc_type is not None or not self._committed:
            self.rollback()

    def commit(self) -> None:
        self._committed = True

    def rollback(self) -> None:
        self._unidades_store.clear()
        self._unidades_store.update(deepcopy(self._snapshot["unidades"]))

        self._cargos_store.clear()
        self._cargos_store.update(deepcopy(self._snapshot["cargos"]))

        self._pagos_store.clear()
        self._pagos_store.update(deepcopy(self._snapshot["pagos"]))

        self._folios_fake._contador = self._snapshot["contador_folio"]
        self._comprobantes_fake._comprobantes.clear()
        self._comprobantes_fake._comprobantes.update(
            deepcopy(self._snapshot["comprobantes"])
        )