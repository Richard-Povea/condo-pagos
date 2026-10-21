from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import Boolean, Date, ForeignKey, Index, Integer, Numeric, String, Text, text
from sqlalchemy import Enum as PgEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from condo_pagos.domain.entities import EstadoCargo, EstadoPago


class Base(DeclarativeBase):
    pass


class UnidadModel(Base):
    __tablename__ = "unidades"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    condominio_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    codigo: Mapped[str] = mapped_column(String(50), nullable=False)
    condominio_nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    activa: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class CargoModel(Base):
    __tablename__ = "cargos"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    unidad_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), 
        ForeignKey("unidades.id"),
        nullable=False
        )
    periodo: Mapped[str] = mapped_column(String(7), nullable=False)  # Formato YYYY-MM
    monto_original: Mapped[Decimal] = mapped_column(Numeric(12, 0), nullable=False)
    saldo: Mapped[Decimal] = mapped_column(Numeric(12, 0), nullable=False)
    vencimiento: Mapped[date] = mapped_column(Date, nullable=False)
    estado: Mapped[EstadoCargo] = mapped_column(
        PgEnum(EstadoCargo, name="estado_cargo_enum", create_type=False),
        nullable=False,
        default=EstadoCargo.PENDIENTE
    )

    __table_args__ = (
        Index("idx_cargos_unidad_saldo", "unidad_id", "saldo"),
    )


class PagoModel(Base):
    __tablename__ = "pagos"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    unidad_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), 
        ForeignKey("unidades.id"), 
        nullable=False
        )
    monto: Mapped[Decimal] = mapped_column(Numeric(12, 0), nullable=False)
    metodo_pago: Mapped[str] = mapped_column(String(50), nullable=False)
    referencia: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True)
    residente_nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    folio: Mapped[str] = mapped_column(String(20), nullable=False)
    exceso: Mapped[Decimal] = mapped_column(Numeric(12, 0), default=Decimal("0"), nullable=False)
    estado: Mapped[EstadoPago] = mapped_column(
        PgEnum(EstadoPago, name="estado_pago_enum", create_type=False),
        nullable=False,
        default=EstadoPago.VIGENTE
    )

    __table_args__ = (
        Index(
            "uq_pagos_referencia",
            "unidad_id",
            "metodo_pago",
            "referencia",
            unique=True,
            postgresql_where=text("referencia IS NOT NULL AND estado = 'VIGENTE'"),
        ),
    )


class FolioSequenceModel(Base):
    __tablename__ = "folios_secuencia"

    anio: Mapped[str] = mapped_column(String(4), primary_key=True)
    ultimo_numero: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class ComprobanteModel(Base):
    __tablename__ = "comprobantes"

    folio: Mapped[str] = mapped_column(String(20), primary_key=True)
    fecha_emision: Mapped[date] = mapped_column(Date, nullable=False)
    unidad_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    residente_nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    monto_pagado: Mapped[Decimal] = mapped_column(Numeric(12, 0), nullable=False)
    metodo_pago: Mapped[str] = mapped_column(String(50), nullable=False)
    exceso: Mapped[Decimal] = mapped_column(Numeric(12, 0), nullable=False)
    hash_anterior: Mapped[str | None] = mapped_column(String(64), nullable=True)
    hash_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    pdf_ruta: Mapped[str | None] = mapped_column(Text, nullable=True)
    datos_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)