from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from condo_pagos.domain.errors import DominioError, MontoInvalidoError
from condo_pagos.domain.money import cuantizar, parsear_monto


class EstadoCargo(StrEnum):
    PENDIENTE = "PENDIENTE"
    PAGADO = "PAGADO"
    ANULADO = "ANULADO"


class MetodoPago(StrEnum):
    EFECTIVO = "EFECTIVO"
    TRANSFERENCIA = "TRANSFERENCIA"
    TARJETA = "TARJETA"


METODOS_HABILITADOS = frozenset({MetodoPago.EFECTIVO, MetodoPago.TRANSFERENCIA})


@dataclass
class Cargo:
    id: UUID
    unidad_id: UUID
    periodo: str  # Formato "YYYY-MM"
    monto_original: Decimal
    saldo: Decimal
    vencimiento: date
    estado: EstadoCargo = EstadoCargo.PENDIENTE
    id_coopropiedad: int | None = None  # Opcional según diseño del arquitecto

    def __post_init__(self) -> None:
        self.monto_original = cuantizar(self.monto_original)
        self.saldo = cuantizar(self.saldo)

    def aplicar(self, monto: Decimal) -> Decimal:
        """Aplica un abono/pago al cargo y devuelve el exceso si lo hubiera."""
        monto_limpio = parsear_monto(monto)
        if self.estado == EstadoCargo.ANULADO:
            raise DominioError("No se puede aplicar un pago a un cargo anulado.")
        if self.estado == EstadoCargo.PAGADO:
            raise DominioError("El cargo ya se encuentra totalmente pagado.")
        if monto_limpio <= Decimal("0"):
            raise MontoInvalidoError("El monto a aplicar debe ser mayor a cero.")
        if monto_limpio >= self.saldo:
            exceso = monto_limpio - self.saldo
            self.saldo = Decimal("0")
            self.estado = EstadoCargo.PAGADO
            return exceso
        self.saldo = cuantizar(self.saldo - monto_limpio)
        return Decimal("0")

    def revertir(self, monto: Decimal) -> None:
        """Revierte un pago aplicado (usado en anulación de pagos)."""
        monto_limpio = parsear_monto(monto)
        if monto_limpio <= Decimal("0"):
            raise MontoInvalidoError("El monto a revertir debe ser mayor a cero.")
        nuevo_saldo = self.saldo + monto_limpio
        if nuevo_saldo > self.monto_original:
            raise DominioError("El saldo revertido no puede superar el monto original del cargo.")
        self.saldo = cuantizar(nuevo_saldo)
        if self.saldo > Decimal("0"):
            self.estado = EstadoCargo.PENDIENTE

    def esta_pendiente(self) -> bool:
        """Indica si el cargo tiene saldo por cobrar y no está anulado."""
        return self.saldo > Decimal("0") and self.estado != EstadoCargo.ANULADO


class EstadoPago(StrEnum):
    VIGENTE = "VIGENTE"
    ANULADO = "ANULADO"


@dataclass
class Pago:
    id: UUID
    unidad_id: UUID
    monto: Decimal
    metodo_pago: str
    referencia: str | None
    residente_nombre: str
    fecha: date
    folio: str
    registrado_por: str
    exceso: Decimal = Decimal("0")
    estado: EstadoPago = EstadoPago.VIGENTE
    anulado_en: datetime | None = None
    anulado_por: str | None = None
    motivo_anulacion: str | None = None
    _condominio_id: UUID | None = field(default=None, init=False, repr=False, compare=False)

    @property
    def condominio_id(self) -> UUID | None:
        """Condominio determinado por la base de datos; no se acepta desde el comando."""
        return self._condominio_id

    def _establecer_condominio_id(self, condominio_id: UUID) -> None:
        if self._condominio_id is not None and self._condominio_id != condominio_id:
            raise DominioError("No se puede cambiar el condominio asociado al pago.")
        self._condominio_id = condominio_id

    def __post_init__(self) -> None:
        self.monto = cuantizar(self.monto)
        self.exceso = cuantizar(self.exceso)

