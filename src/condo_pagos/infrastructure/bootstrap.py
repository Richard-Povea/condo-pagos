"""Construcción del contenedor PostgreSQL para la aplicación."""

from __future__ import annotations

import json
import logging
import os
from datetime import date
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID, uuid4

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from condo_pagos.config import Settings
from condo_pagos.domain.comprobante import ComprobanteData
from condo_pagos.domain.errors import DominioError
from condo_pagos.infrastructure.pdf_generator.reportlab_renderer import ReportLabPdfRenderer
from condo_pagos.infrastructure.database.schema import verificar_esquema
from condo_pagos.infrastructure.database.queries import ConsultasPostgres
from condo_pagos.infrastructure.database.unit_of_work import SqlAlchemyUnitOfWork
from condo_pagos.use_cases.anular_pago import AnularPagoUseCase
from condo_pagos.use_cases.dto import (
    EstadoCuentaDTO,
    RegistrarPagoCmd,
    ResultadoPagosDTO,
    UnidadConsultaDTO,
)
from condo_pagos.use_cases.registrar_pago import RegistrarPagoUseCase

log = logging.getLogger(__name__)


class PostgresContainer:
    """Adaptador que expone las operaciones que consume la UI."""

    nombre_condominio = "Condominio Principal"

    def __init__(self, settings: Settings) -> None:
        self._engine = create_engine(
            settings.condo_database_url,
            pool_pre_ping=True,
            future=True,
            connect_args={
                "connect_timeout": 5,
                "options": "-c search_path=gc,public",
            },
            poolclass=NullPool,
        )
        log.info(
            "Configurando conexión PostgreSQL: %s",
            self._engine.url.render_as_string(hide_password=True),
        )
        self._session_factory = sessionmaker(
            bind=self._engine, expire_on_commit=False, future=True
        )
        self._consultas = ConsultasPostgres(self._session_factory)
        self._uow_factory = lambda: SqlAlchemyUnitOfWork(self._session_factory)
        self._pdf_dir = settings.pdf_dir
        verificar_esquema(self._engine)
        self._verificar_directorio_pdf()

    def _verificar_directorio_pdf(self) -> None:
        """Advierte si no se pueden guardar comprobantes, sin bloquear pagos."""
        try:
            self._pdf_dir.mkdir(parents=True, exist_ok=True)
            if not os.access(self._pdf_dir, os.W_OK):
                raise OSError("el directorio no tiene permisos de escritura")
        except OSError:
            log.warning(
                "No se pueden guardar comprobantes PDF en %s. "
                "El registro de pagos seguirá disponible.",
                self._pdf_dir,
            )

    @staticmethod
    def _unidad(row) -> SimpleNamespace:
        return SimpleNamespace(
            unidad_id=row.id,
            id=row.id,
            identificador=row.codigo,
            codigo=row.codigo,
            responsable="",
            rut="",
            condominio_nombre=row.condominio_nombre,
            activa=row.activa,
            saldo_total=Decimal(str(row.saldo_total or 0)),
        )

    def listar_unidades(self, solo_morosas: bool = False) -> list[UnidadConsultaDTO]:
        """Lista unidades y saldos delegando la lectura al adaptador de consultas."""
        return self._consultas.listar_unidades(solo_morosas=solo_morosas)

    def buscar_unidades(self, texto: str = "") -> list[UnidadConsultaDTO]:
        """Busca unidades delegando la lectura al adaptador de consultas."""
        return self._consultas.buscar_unidades(texto)

    def consultar_estado_cuenta(self, unidad_id: UUID | str) -> EstadoCuentaDTO:
        """Consulta el estado de cuenta tipado de una unidad."""
        return self._consultas.consultar_estado_cuenta(unidad_id)

    def registrar_pago(
        self, *, unidad_id: UUID | str, monto: Decimal | int | str,
        metodo_pago: str = "EFECTIVO", referencia: str = "",
        operador: str = "", fecha: date | None = None,
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
            folio=resultado.folio, pago_id=resultado.folio,
            monto_pagado=resultado.monto_pagado, pdf_ruta=resultado.pdf_ruta,
        )

    def listar_pagos(
        self, *, filtros: dict | None = None, pagina: int = 1, limite: int = 50,
    ) -> ResultadoPagosDTO:
        """Lista pagos con filtros y paginación desde el adaptador de consultas."""
        return self._consultas.listar_pagos(
            filtros=filtros, pagina=pagina, limite=limite
        )

    def anular_pago(
        self, *, pago_id: str, motivo: str = "", operador: str = "",
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
                text("SELECT folio FROM pagos WHERE id = :id"), {"id": pago_uuid}
            ).scalar_one_or_none()
        if folio is None:
            raise ValueError(f"No se encontró el pago {pago_id}")
        AnularPagoUseCase(self._uow_factory()).ejecutar(pago_uuid)
        return folio

    def emitir_pdf(self, comprobante_id: str) -> str:
        """Genera el PDF usando el renderer oficial y el snapshot guardado."""
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

        # Los comprobantes son inmutables: el trigger de PostgreSQL bloquea
        # cualquier UPDATE, incluido pdf_ruta. El archivo generado se devuelve
        # directamente sin intentar modificar el snapshot persistido.
        return str(ruta)


def build_container(settings: Settings | None = None) -> PostgresContainer:
    """Construye y valida el contenedor de producción."""
    return PostgresContainer(settings or Settings())
