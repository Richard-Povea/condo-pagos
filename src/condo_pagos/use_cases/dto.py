from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from condo_pagos.domain.comprobante import LineaCargo


@dataclass(frozen=True)
class UnidadInfo:
    id: UUID
    condominio_id: UUID
    codigo: str
    condominio_nombre: str
    activa: bool


@dataclass(frozen=True)
class RegistrarPagoCmd:
    unidad_id: UUID
    monto: Decimal
    metodo_pago: str  # Ej: "TRANSFERENCIA", "EFECTIVO", "WEBPAY"
    referencia: str
    residente_nombre: str
    fecha_pago: date


@dataclass(frozen=True)
class ComprobanteEmitido:
    folio: str
    fecha_emision: date
    unidad_id: UUID
    residente_nombre: str
    monto_pagado: Decimal
    exceso: Decimal
    pdf_ruta: str | None
    hash_sha256: str
    lineas: tuple[LineaCargo, ...]


@dataclass(frozen=True)
class CargoPendienteDTO:
    id: UUID
    periodo: str
    monto_original: Decimal
    saldo: Decimal
    vencimiento: date


@dataclass(frozen=True)
class PagoRecienteDTO:
    id: UUID
    folio: str
    fecha: date
    monto: Decimal
    metodo_pago: str
    estado: str


@dataclass(frozen=True)
class EstadoCuentaDTO:
    unidad_id: UUID
    codigo_unidad: str
    total_adeudado: Decimal
    cargos_pendientes: tuple[CargoPendienteDTO, ...]
    pagos_recientes: tuple[PagoRecienteDTO, ...]