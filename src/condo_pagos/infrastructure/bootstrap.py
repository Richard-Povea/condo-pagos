"""Construcción del contenedor PostgreSQL para la aplicación."""

from __future__ import annotations

import json
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
from condo_pagos.infrastructure.database.bootstrap import ESQUEMA_VERSION_ESPERADA
from condo_pagos.infrastructure.database.unit_of_work import SqlAlchemyUnitOfWork
from condo_pagos.use_cases.anular_pago import AnularPagoUseCase
from condo_pagos.use_cases.dto import RegistrarPagoCmd
from condo_pagos.use_cases.registrar_pago import RegistrarPagoUseCase


class PostgresContainer:
    """Adaptador que expone las operaciones que consume la UI."""

    nombre_condominio = "Condominio Principal"

    def __init__(self, settings: Settings) -> None:
        self._engine = create_engine(
            settings.condo_database_url,
            pool_pre_ping=True,
            future=True,
            connect_args={"options": "-c search_path=gc,public"},
            poolclass=NullPool,
        )
        self._session_factory = sessionmaker(
            bind=self._engine, expire_on_commit=False, future=True
        )
        self._uow_factory = lambda: SqlAlchemyUnitOfWork(self._session_factory)
        self._pdf_dir = settings.pdf_dir
        self._verificar_esquema()

    def _verificar_esquema(self) -> None:
        try:
            with self._engine.connect() as connection:
                version = connection.execute(
                    text("SELECT version FROM gc.schema_info")
                ).scalar_one_or_none()
        except Exception as exc:
            raise RuntimeError(
                "No se pudo verificar el esquema PostgreSQL (gc.schema_info)."
            ) from exc
        if version != ESQUEMA_VERSION_ESPERADA:
            raise RuntimeError(
                f"Versión de esquema incompatible: {version!r}; "
                f"se requiere {ESQUEMA_VERSION_ESPERADA}."
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

    def listar_unidades(self, solo_morosas: bool = False) -> list[SimpleNamespace]:
        sql = """
            SELECT u.id, u.codigo, u.condominio_nombre, u.activa,
                   COALESCE(SUM(c.saldo), 0) AS saldo_total
            FROM unidades u
            LEFT JOIN cargos c ON c.unidad_id = u.id AND c.estado = 'PENDIENTE'
            WHERE u.activa IS TRUE
            GROUP BY u.id, u.codigo, u.condominio_nombre, u.activa
        """
        if solo_morosas:
            sql += " HAVING COALESCE(SUM(c.saldo), 0) > 0"
        sql += " ORDER BY u.codigo"
        with self._session_factory() as session:
            rows = session.execute(text(sql)).fetchall()
        return [self._unidad(row) for row in rows]

    def buscar_unidades(self, texto: str = "") -> list[SimpleNamespace]:
        criterio = texto.strip()
        with self._session_factory() as session:
            rows = session.execute(
                text("""
                    SELECT u.id, u.codigo, u.condominio_nombre, u.activa,
                           COALESCE(SUM(c.saldo), 0) AS saldo_total
                    FROM unidades u
                    LEFT JOIN cargos c ON c.unidad_id = u.id AND c.estado = 'PENDIENTE'
                    WHERE u.activa IS TRUE
                      AND (:criterio = '' OR u.codigo ILIKE :patron
                           OR u.condominio_nombre ILIKE :patron)
                    GROUP BY u.id, u.codigo, u.condominio_nombre, u.activa
                    ORDER BY u.codigo
                """),
                {"criterio": criterio, "patron": f"%{criterio}%"},
            ).fetchall()
        return [self._unidad(row) for row in rows]

    def consultar_estado_cuenta(self, unidad_id: UUID | str) -> SimpleNamespace:
        try:
            identificador = UUID(str(unidad_id))
        except ValueError as exc:
            raise ValueError(f"Identificador de unidad inválido: {unidad_id}") from exc
        with self._session_factory() as session:
            unidad = session.execute(
                text("""
                    SELECT id, codigo, condominio_nombre, activa
                    FROM unidades WHERE id = :id
                """), {"id": identificador}
            ).fetchone()
            if unidad is None:
                raise ValueError(f"No existe la unidad {unidad_id}")
            cargos = session.execute(
                text("""
                    SELECT id, periodo, monto_original, saldo, vencimiento
                    FROM cargos WHERE unidad_id = :id AND saldo > 0
                      AND estado = 'PENDIENTE'
                    ORDER BY vencimiento, periodo
                """), {"id": identificador}
            ).fetchall()
            pagos = session.execute(
                text("""
                    SELECT id, folio, fecha, monto, metodo_pago, estado
                    FROM pagos WHERE unidad_id = :id
                    ORDER BY fecha DESC LIMIT 10
                """), {"id": identificador}
            ).fetchall()
        total = sum((Decimal(str(c.saldo)) for c in cargos), Decimal("0"))
        return SimpleNamespace(
            unidad_id=identificador, codigo_unidad=unidad.codigo,
            total_adeudado=total, cargos_pendientes=cargos, pagos_recientes=pagos,
        )

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
    ) -> SimpleNamespace:
        filtros = filtros or {}
        condiciones = [
            "(:texto = '' OR p.folio ILIKE :patron OR u.codigo ILIKE :patron "
            "OR p.residente_nombre ILIKE :patron)"
        ]
        texto_filtro = str(filtros.get("texto") or "").strip()
        params = {
            "texto": texto_filtro, "patron": f"%{texto_filtro}%",
            "limite": max(1, limite), "offset": max(0, pagina - 1) * max(1, limite),
        }
        for key, column in (("metodo", "p.metodo_pago"), ("estado", "p.estado")):
            value = str(filtros.get(key) or "").strip()
            if value:
                condiciones.append(f"{column}::text ILIKE :{key}")
                params[key] = f"%{value}%"
        for key, op in (("fecha_desde", ">="), ("fecha_hasta", "<=")):
            value = filtros.get(key)
            if value:
                condiciones.append(f"p.fecha {op} :{key}")
                params[key] = value
        where = " AND ".join(condiciones)
        with self._session_factory() as session:
            total = session.execute(
                text(
                    f"SELECT count(*) FROM pagos p JOIN unidades u ON u.id=p.unidad_id "
                    f"WHERE {where}"
                ), params,
            ).scalar_one()
            rows = session.execute(
                text(f"""
                    SELECT p.id, p.folio, p.fecha, u.codigo AS unidad,
                           p.residente_nombre AS pagador, p.monto,
                           p.metodo_pago AS metodo, p.estado::text AS estado,
                           p.referencia
                    FROM pagos p JOIN unidades u ON u.id=p.unidad_id
                    WHERE {where}
                    ORDER BY p.fecha DESC, p.folio DESC
                    LIMIT :limite OFFSET :offset
                """), params,
            ).fetchall()
        return SimpleNamespace(
            filas=[SimpleNamespace(
                pago_id=row.id, folio=row.folio, fecha=row.fecha, unidad=row.unidad,
                pagador=row.pagador, monto=Decimal(str(row.monto)), metodo=row.metodo,
                estado=row.estado, referencia=row.referencia,
            ) for row in rows],
            total_paginas=(total + limite - 1) // limite if total else 0,
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
                    SELECT c.folio, c.datos_json
                    FROM comprobantes c
                    WHERE c.folio = :folio
                       OR c.folio = (
                           SELECT p.folio FROM pagos p WHERE p.id::text = :identificador
                       )
                """),
                {"folio": comprobante_id, "identificador": comprobante_id},
            ).fetchone()
        if row is None:
            raise ValueError(f"No existe el comprobante {comprobante_id}")

        snapshot = ComprobanteData.desde_json(json.dumps(row.datos_json, ensure_ascii=False))
        contenido_pdf = ReportLabPdfRenderer().renderizar(snapshot)
        self._pdf_dir.mkdir(parents=True, exist_ok=True)
        ruta = self._pdf_dir / f"comprobante_{row.folio}.pdf"
        ruta.write_bytes(contenido_pdf)

        with self._session_factory.begin() as session:
            session.execute(
                text("UPDATE comprobantes SET pdf_ruta = :ruta WHERE folio = :folio"),
                {"ruta": str(ruta), "folio": row.folio},
            )
        return str(ruta)


def build_container(settings: Settings | None = None) -> PostgresContainer:
    """Construye y valida el contenedor de producción."""
    return PostgresContainer(settings or Settings())
