import json
from collections.abc import Callable
from datetime import datetime
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from condo_pagos.domain.comprobante import ComprobanteData
from condo_pagos.domain.entities import Cargo, EstadoCargo, EstadoPago, Pago
from condo_pagos.domain.errors import DominioError
from condo_pagos.infrastructure.database.models import (
    CargoModel,
    ComprobanteModel,
    PagoModel,
    UnidadModel,
)
from condo_pagos.use_cases.dto import UnidadInfo
from condo_pagos.use_cases.ports import (
    CargosRepository,
    ComprobantesRepository,
    FoliosRepository,
    PagosRepository,
    UnidadesRepository,
    UnitOfWork,
)


class SqlAlchemyUnidadesRepository(UnidadesRepository):
    def __init__(self, session: Session) -> None:
        self.session = session

    def obtener_por_id(self, unidad_id: UUID) -> UnidadInfo | None:
        model = self.session.get(UnidadModel, unidad_id)
        if not model:
            return None
        return UnidadInfo(
            id=model.id,
            condominio_id=model.condominio_id,
            codigo=model.codigo,
            condominio_nombre=model.condominio_nombre,
            activa=model.activa,
        )


class SqlAlchemyCargosRepository(CargosRepository):
    def __init__(self, session: Session) -> None:
        self.session = session

    def obtener_pendientes_por_unidad(self, unidad_id: UUID) -> list[Cargo]:
        stmt = text(
            """
            SELECT id, unidad_id, periodo, monto_original, saldo, vencimiento, estado
            FROM cargos
            WHERE unidad_id = :unidad_id AND saldo > 0 AND estado != 'ANULADO'
            ORDER BY vencimiento ASC, periodo ASC
            """
        )
        result = self.session.execute(stmt, {"unidad_id": unidad_id}).fetchall()
        return [
            Cargo(
                id=row.id,
                unidad_id=row.unidad_id,
                periodo=row.periodo,
                monto_original=row.monto_original,
                saldo=row.saldo,
                vencimiento=row.vencimiento,
                estado=EstadoCargo(row.estado),
            )
            for row in result
        ]

    def guardar(self, cargo: Cargo) -> None:
        model = self.session.get(CargoModel, cargo.id)
        if model:
            model.saldo = cargo.saldo
            model.estado = cargo.estado
        else:
            new_model = CargoModel(
                id=cargo.id,
                unidad_id=cargo.unidad_id,
                periodo=cargo.periodo,
                monto_original=cargo.monto_original,
                saldo=cargo.saldo,
                vencimiento=cargo.vencimiento,
                estado=cargo.estado,
            )
            self.session.add(new_model)

    def bloquear_para_actualizacion(self, cargo_ids: list[UUID]) -> list[Cargo]:
        if not cargo_ids:
            return []
        stmt = text(
            """
            SELECT id, unidad_id, periodo, monto_original, saldo, vencimiento, estado
            FROM cargos
            WHERE id = ANY(:cargo_ids)
            FOR UPDATE
            """
        )
        result = self.session.execute(stmt, {"cargo_ids": cargo_ids}).fetchall()
        return [
            Cargo(
                id=row.id,
                unidad_id=row.unidad_id,
                periodo=row.periodo,
                monto_original=row.monto_original,
                saldo=row.saldo,
                vencimiento=row.vencimiento,
                estado=EstadoCargo(row.estado),
            )
            for row in result
        ]


class SqlAlchemyPagosRepository(PagosRepository):
    def __init__(self, session: Session) -> None:
        self.session = session

    def guardar(self, pago: Pago) -> None:
        # Estándar: upsert basado en session.get() por ID
        model = self.session.get(PagoModel, pago.id)
        if model:
            model.estado = pago.estado
            model.exceso = pago.exceso
        else:
            new_model = PagoModel(
                id=pago.id,
                unidad_id=pago.unidad_id,
                monto=pago.monto,
                metodo_pago=pago.metodo_pago,
                referencia=pago.referencia,
                residente_nombre=pago.residente_nombre,
                fecha=pago.fecha,
                folio=pago.folio,
                exceso=pago.exceso,
                estado=pago.estado,
            )
            self.session.add(new_model)

    def obtener_por_id(self, pago_id: UUID) -> Pago | None:
        model = self.session.get(PagoModel, pago_id)
        if not model:
            return None
        return Pago(
            id=model.id,
            unidad_id=model.unidad_id,
            monto=model.monto,
            metodo_pago=model.metodo_pago,
            referencia=model.referencia,
            residente_nombre=model.residente_nombre,
            fecha=model.fecha,
            folio=model.folio,
            exceso=model.exceso,
            estado=EstadoPago(model.estado),
        )
    
    def existe_por_referencia(self, referencia: str | None) -> bool:
        if referencia is None:
            return False
        stmt = text(
            "SELECT 1 FROM pagos WHERE referencia = :referencia AND estado = 'VIGENTE'"
        )
        res = self.session.execute(stmt, {"referencia": referencia}).fetchone()
        return res is not None

    def listar_recientes_por_unidad(self, unidad_id: UUID, limite: int = 10) -> list[Pago]:
        stmt = text(
            """
            SELECT id, unidad_id, monto, metodo_pago, referencia, 
                   residente_nombre, fecha, folio, exceso, estado
            FROM pagos
            WHERE unidad_id = :unidad_id
            ORDER BY fecha DESC
            LIMIT :limite
            """
        )
        result = self.session.execute(stmt, {"unidad_id": unidad_id, "limite": limite}).fetchall()
        return [
            Pago(
                id=row.id,
                unidad_id=row.unidad_id,
                monto=row.monto,
                metodo_pago=row.metodo_pago,
                referencia=row.referencia,
                residente_nombre=row.residente_nombre,
                fecha=row.fecha,
                folio=row.folio,
                exceso=row.exceso,
                estado=EstadoPago(row.estado),
            )
            for row in result
        ]


class SqlAlchemyFoliosRepository(FoliosRepository):
    def __init__(self, session: Session) -> None:
        self.session = session

    def siguiente_folio(self) -> str:
        # Obtener año actual en zona horaria de Chile para evitar desfases de cambio de año
        ahora_cl = datetime.now(ZoneInfo("America/Santiago"))
        anio_str = str(ahora_cl.year)

        # Upsert atómico en la tabla de folios
        stmt = text(
            """
            INSERT INTO folios_secuencia (anio, ultimo_numero)
            VALUES (:anio, 1)
            ON CONFLICT (anio)
            DO UPDATE SET ultimo_numero = folios_secuencia.ultimo_numero + 1
            RETURNING ultimo_numero
            """
        )
        res = self.session.execute(stmt, {"anio": anio_str}).scalar_one()
        return f"{anio_str}-{res:06d}"


class SqlAlchemyComprobantesRepository(ComprobantesRepository):
    def __init__(self, session: Session) -> None:
        self.session = session

    def guardar(self, comprobante: ComprobanteData, pdf_ruta: str | None) -> None:
        model = ComprobanteModel(
            folio=comprobante.folio,
            fecha_emision=comprobante.fecha_emision,
            unidad_id=comprobante.unidad_id,
            residente_nombre=comprobante.residente_nombre,
            monto_pagado=comprobante.monto_pagado,
            metodo_pago=comprobante.metodo_pago,
            exceso=comprobante.exceso,
            hash_anterior=comprobante.hash_anterior,
            hash_sha256=comprobante.hash_sha256(),
            pdf_ruta=pdf_ruta,
            datos_json=comprobante.a_dict(),
        )
        self.session.add(model)

    def obtener_por_folio(self, folio: str) -> ComprobanteData | None:
        model = self.session.get(ComprobanteModel, folio)
        if not model:
            return None
        return ComprobanteData.desde_json(json.dumps(model.datos_json))

    def actualizar_ruta_pdf(self, folio: str, pdf_ruta: str) -> None:
        model = self.session.get(ComprobanteModel, folio)
        if model:
            model.pdf_ruta = pdf_ruta


class SqlAlchemyUnitOfWork(UnitOfWork):
    def __init__(self, session_factory: Callable[[], Session] | None = None) -> None:
        from condo_pagos.infrastructure.database.engine import SessionLocal
        self.session_factory = session_factory or SessionLocal

    def __enter__(self) -> "SqlAlchemyUnitOfWork":
        self.session: Session = self.session_factory()
        self.unidades = SqlAlchemyUnidadesRepository(self.session)
        self.cargos = SqlAlchemyCargosRepository(self.session)
        self.pagos = SqlAlchemyPagosRepository(self.session)
        self.folios = SqlAlchemyFoliosRepository(self.session)
        self.comprobantes = SqlAlchemyComprobantesRepository(self.session)
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        if exc_type is not None:
            self.rollback()
        self.session.close()

    def commit(self) -> None:
        try:
            self.session.commit()
        except IntegrityError as e:
            self.session.rollback()
            # Traducción de errores según regla de negocio (ej. referencia duplicada)
            error_msg = str(e.orig)
            if "uq_pagos_referencia" in error_msg or "pagos_referencia_key" in error_msg:
                raise DominioError("Ya existe un pago registrado con esa referencia.") from e
            raise

    def rollback(self) -> None:
        self.session.rollback()