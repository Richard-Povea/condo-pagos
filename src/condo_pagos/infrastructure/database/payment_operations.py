"""Adaptador de operaciones de pago y comprobantes sobre PostgreSQL."""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from typing import Callable
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.orm import Session

from condo_pagos.domain.comprobante import ComprobanteData
from condo_pagos.domain.errors import DominioError
from condo_pagos.infrastructure.database.unit_of_work import SqlAlchemyUnitOfWork
from condo_pagos.infrastructure.pdf_generator.reportlab_renderer import ReportLabPdfRenderer
from condo_pagos.use_cases.anular_pago import AnularPagoUseCase
from condo_pagos.use_cases.dto import RegistrarPagoCmd
from condo_pagos.use_cases.registrar_pago import RegistrarPagoUseCase


class OperacionesPagoPostgres:
    """Orquesta escrituras y generación de PDF sin mezclar consultas de lectura."""

    def __init__(
        self,
        session_factory: Callable[[], Session],
        uow_factory: Callable[[], SqlAlchemyUnitOfWork],
        pdf_dir: Path,
    ) -> None:
        self._session_factory = session_factory
        self._uow_factory = uow_factory
        self._pdf_dir = pdf_dir

    def registrar_pago(
        self,
        *,
        unidad_id: UUID | str,
        monto: Decimal | int | str,
        metodo_pago: str = "EFECTIVO",
        referencia: str = "",
        operador: str = "",
        fecha: date | None = None,
    ) -> SimpleNamespace:
        try:
            unidad_uuid = UUID(str(unidad_id))
        except ValueError as exc:
            raise ValueError(f"Identificador de unidad inválido: {unidad_id}") from exc

        with self._session_factory() as session:
            unidad = session.execute(
                text("SELECT codigo FROM unidades WHERE id = :id"),
                {"id": unidad_uuid},
            ).fetchone()
        if unidad is None:
            raise DominioError(f"La unidad {unidad_id} no existe.")

        cmd = RegistrarPagoCmd(
            unidad_id=unidad_uuid,
            monto=Decimal(str(monto)),
            metodo_pago=metodo_pago,
            referencia=referencia or f"MANUAL-{unidad_uuid}-{uuid4().hex}",
            residente_nombre=operador or "Operador",
            fecha_pago=fecha or date.today(),
        )
        resultado = RegistrarPagoUseCase(self._uow_factory()).ejecutar(cmd)
        return SimpleNamespace(
            folio=resultado.folio,
            pago_id=resultado.folio,
            monto_pagado=resultado.monto_pagado,
            pdf_ruta=resultado.pdf_ruta,
        )

    def anular_pago(
        self, *, pago_id: str, motivo: str = "", operador: str = ""
    ) -> str:
        try:
            pago_uuid = UUID(str(pago_id))
        except ValueError:
            with self._session_factory() as session:
                pago_uuid = session.execute(
                    text("SELECT id FROM pagos WHERE folio = :folio"),
                    {"folio": pago_id},
                ).scalar_one_or_none()
            if pago_uuid is None:
                raise ValueError(f"No se encontró el pago {pago_id}")

        with self._session_factory() as session:
            folio = session.execute(
                text("SELECT folio FROM pagos WHERE id = :id"),
                {"id": pago_uuid},
            ).scalar_one_or_none()
        if folio is None:
            raise ValueError(f"No se encontró el pago {pago_id}")

        AnularPagoUseCase(self._uow_factory()).ejecutar(pago_uuid)
        return folio

    def emitir_pdf(self, comprobante_id: str) -> str:
        """Regenera el PDF desde el snapshot inmutable guardado en la base."""
        with self._session_factory() as session:
            row = session.execute(
                text("""
                    SELECT c.folio, c.datos_json, u.codigo AS unidad_codigo
                    FROM comprobantes c
                    JOIN unidades u ON u.id = c.unidad_id
                    WHERE c.folio = :folio
                       OR c.folio = (
                           SELECT p.folio FROM pagos p WHERE p.id::text = :identificador
                       )
                """),
                {"folio": comprobante_id, "identificador": comprobante_id},
            ).fetchone()
        if row is None:
            raise ValueError(f"No existe el comprobante {comprobante_id}")

        datos_json = (
            row.datos_json
            if isinstance(row.datos_json, str)
            else json.dumps(row.datos_json, ensure_ascii=False)
        )
        snapshot = ComprobanteData.desde_json(datos_json)
        contenido_pdf = ReportLabPdfRenderer().renderizar(
            snapshot, unidad_codigo=row.unidad_codigo
        )
        self._pdf_dir.mkdir(parents=True, exist_ok=True)
        ruta = self._pdf_dir / f"comprobante_{row.folio}.pdf"
        ruta.write_bytes(contenido_pdf)
        # El comprobante es inmutable; no se actualiza pdf_ruta en la base.
        return str(ruta)
