from abc import abstractmethod
from typing import Protocol
from uuid import UUID

from condo_pagos.domain.comprobante import ComprobanteData
from condo_pagos.domain.entities import Cargo, Pago
from condo_pagos.use_cases.dto import UnidadInfo


class UnidadesRepository(Protocol):
    @abstractmethod
    def obtener_por_id(self, unidad_id: UUID) -> UnidadInfo | None:
        ...


class CargosRepository(Protocol):
    @abstractmethod
    def obtener_pendientes_por_unidad(self, unidad_id: UUID) -> list[Cargo]:
        ...

    @abstractmethod
    def guardar(self, cargo: Cargo) -> None:
        ...

    @abstractmethod
    def bloquear_para_actualizacion(self, cargo_ids: list[UUID]) -> list[Cargo]:
        """Bloquea los registros en BD 
        para evitar condiciones de carrera concurrentes (SELECT ... FOR UPDATE)."""
        ...


class PagosRepository(Protocol):
    @abstractmethod
    def guardar(self, pago: Pago) -> None:
        ...

    @abstractmethod
    def obtener_por_id(self, pago_id: UUID) -> Pago | None:
        ...

    @abstractmethod
    def existe_por_referencia(self, referencia: str | None) -> bool:
        ...

    @abstractmethod
    def listar_recientes_por_unidad(self, unidad_id: UUID, limite: int = 10) -> list[Pago]:
        ...


class FoliosRepository(Protocol):
    @abstractmethod
    def siguiente_folio(self) -> str:
        """Genera o reserva el siguiente folio correlativo (ej: '2026-000001')."""
        ...


class ComprobantesRepository(Protocol):
    @abstractmethod
    def guardar(self, comprobante: ComprobanteData, pdf_ruta: str | None) -> None:
        ...

    @abstractmethod
    def obtener_por_folio(self, folio: str) -> ComprobanteData | None:
        ...

    @abstractmethod
    def actualizar_ruta_pdf(self, folio: str, pdf_ruta: str) -> None:
        ...


class PdfRenderer(Protocol):
    @abstractmethod
    def renderizar(self, comprobante: ComprobanteData) -> bytes:
        """Renderiza el PDF del comprobante y retorna los bytes crudos."""
        ...


class ComprobanteStorage(Protocol):
    @abstractmethod
    def guardar(self, folio: str, contenido_pdf: bytes) -> str:
        """Guarda el PDF en disco/almacenamiento y retorna la ruta o URI final."""
        ...


class UnitOfWork(Protocol):
    cargos: CargosRepository
    pagos: PagosRepository
    folios: FoliosRepository
    comprobantes: ComprobantesRepository
    unidades: UnidadesRepository

    @abstractmethod
    def __enter__(self) -> "UnitOfWork":
        ...

    @abstractmethod
    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        ...

    @abstractmethod
    def commit(self) -> None:
        ...

    @abstractmethod
    def rollback(self) -> None:
        ...