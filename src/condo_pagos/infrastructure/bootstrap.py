"""Construcción del contenedor PostgreSQL para la aplicación."""

from __future__ import annotations

import logging
import os
from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from condo_pagos.config import Settings
from condo_pagos.infrastructure.database.payment_operations import OperacionesPagoPostgres
from condo_pagos.infrastructure.database.queries import ConsultasPostgres
from condo_pagos.infrastructure.database.schema import verificar_esquema
from condo_pagos.infrastructure.database.unit_of_work import SqlAlchemyUnitOfWork
from condo_pagos.use_cases.dto import (
    EstadoCuentaDTO,
    ResultadoPagosDTO,
    UnidadConsultaDTO,
)

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
        self._operaciones_pago = OperacionesPagoPostgres(
            self._session_factory, self._uow_factory, self._pdf_dir
        )
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
        self,
        *,
        unidad_id: UUID | str,
        monto: Decimal | int | str,
        metodo_pago: str = "EFECTIVO",
        referencia: str = "",
        operador: str = "",
        fecha: date | None = None,
    ) -> Any:
        """Registra un pago mediante el adaptador de operaciones."""
        return self._operaciones_pago.registrar_pago(
            unidad_id=unidad_id,
            monto=monto,
            metodo_pago=metodo_pago,
            referencia=referencia,
            operador=operador,
            fecha=fecha,
        )

    def listar_pagos(
        self, *, filtros: dict[str, Any] | None = None, pagina: int = 1, limite: int = 50,
    ) -> ResultadoPagosDTO:
        """Lista pagos con filtros y paginación desde el adaptador de consultas."""
        return self._consultas.listar_pagos(
            filtros=filtros, pagina=pagina, limite=limite
        )

    def anular_pago(
        self, *, pago_id: str, motivo: str = "", operador: str = ""
    ) -> str:
        """Anula un pago mediante el adaptador de operaciones."""
        return self._operaciones_pago.anular_pago(
            pago_id=pago_id, motivo=motivo, operador=operador
        )

    def emitir_pdf(self, comprobante_id: str) -> str:
        """Genera el comprobante desde el snapshot persistido."""
        return self._operaciones_pago.emitir_pdf(comprobante_id)


def build_container(settings: Settings | None = None) -> PostgresContainer:
    """Construye y valida el contenedor de producción."""
    return PostgresContainer(settings or Settings())
