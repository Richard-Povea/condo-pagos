"""Consultas de lectura PostgreSQL, separadas de la composición del contenedor."""

from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from condo_pagos.use_cases.dto import (
    CargoPendienteDTO,
    EstadoCuentaDTO,
    PagoListadoDTO,
    PagoRecienteDTO,
    ResultadoPagosDTO,
    UnidadConsultaDTO,
)


class ConsultasPostgres:
    """Implementa consultas de unidades, estados de cuenta e historial de pagos."""

    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._session_factory = session_factory

    @staticmethod
    def _unidad(row: Any) -> UnidadConsultaDTO:
        return UnidadConsultaDTO(
            unidad_id=row.id,
            identificador=row.codigo,
            condominio_nombre=row.condominio_nombre,
            activa=row.activa,
            saldo_total=Decimal(str(row.saldo_total or 0)),
        )

    def listar_unidades(self, solo_morosas: bool = False) -> list[UnidadConsultaDTO]:
        sql = """
            SELECT u.id, u.codigo, u.condominio_nombre, u.activa,
                   COALESCE(SUM(c.saldo), 0) AS saldo_total
            FROM unidades u
            LEFT JOIN cargos c
              ON c.unidad_id = u.id AND c.estado = 'PENDIENTE' AND c.saldo > 0
            WHERE u.activa IS TRUE
            GROUP BY u.id, u.codigo, u.condominio_nombre, u.activa
        """
        if solo_morosas:
            sql += " HAVING COALESCE(SUM(c.saldo), 0) > 0"
        sql += " ORDER BY u.codigo"
        with self._session_factory() as session:
            rows = session.execute(text(sql)).fetchall()
        return [self._unidad(row) for row in rows]

    def buscar_unidades(self, texto: str = "") -> list[UnidadConsultaDTO]:
        criterio = texto.strip()
        with self._session_factory() as session:
            rows = session.execute(
                text("""
                    SELECT u.id, u.codigo, u.condominio_nombre, u.activa,
                           COALESCE(SUM(c.saldo), 0) AS saldo_total
                    FROM unidades u
                    LEFT JOIN cargos c
                      ON c.unidad_id = u.id AND c.estado = 'PENDIENTE' AND c.saldo > 0
                    WHERE u.activa IS TRUE
                      AND (:criterio = '' OR u.codigo ILIKE :patron
                           OR u.condominio_nombre ILIKE :patron)
                    GROUP BY u.id, u.codigo, u.condominio_nombre, u.activa
                    ORDER BY u.codigo
                """),
                {"criterio": criterio, "patron": f"%{criterio}%"},
            ).fetchall()
        return [self._unidad(row) for row in rows]

    def consultar_estado_cuenta(self, unidad_id: UUID | str) -> EstadoCuentaDTO:
        try:
            identificador = UUID(str(unidad_id))
        except ValueError as exc:
            raise ValueError(f"Identificador de unidad inválido: {unidad_id}") from exc

        with self._session_factory() as session:
            unidad = session.execute(
                text("""
                    SELECT id, codigo FROM unidades WHERE id = :id
                """),
                {"id": identificador},
            ).fetchone()
            if unidad is None:
                raise ValueError(f"No existe la unidad {unidad_id}")

            cargos = session.execute(
                text("""
                    SELECT id, periodo, monto_original, saldo, vencimiento
                    FROM cargos
                    WHERE unidad_id = :id AND saldo > 0 AND estado = 'PENDIENTE'
                    ORDER BY vencimiento, periodo
                """),
                {"id": identificador},
            ).fetchall()
            pagos = session.execute(
                text("""
                    SELECT id, folio, fecha, monto, metodo_pago, estado::text AS estado
                    FROM pagos WHERE unidad_id = :id
                    ORDER BY fecha DESC, folio DESC LIMIT 10
                """),
                {"id": identificador},
            ).fetchall()

        cargos_dto = tuple(
            CargoPendienteDTO(
                id=row.id,
                periodo=row.periodo,
                monto_original=Decimal(str(row.monto_original)),
                saldo=Decimal(str(row.saldo)),
                vencimiento=row.vencimiento,
            )
            for row in cargos
        )
        pagos_dto = tuple(
            PagoRecienteDTO(
                id=row.id,
                folio=row.folio,
                fecha=row.fecha,
                monto=Decimal(str(row.monto)),
                metodo_pago=row.metodo_pago,
                estado=str(row.estado),
            )
            for row in pagos
        )
        return EstadoCuentaDTO(
            unidad_id=identificador,
            codigo_unidad=unidad.codigo,
            total_adeudado=sum(
                (cargo.saldo for cargo in cargos_dto), Decimal("0")
            ),
            cargos_pendientes=cargos_dto,
            pagos_recientes=pagos_dto,
        )

    def listar_pagos(
        self,
        *,
        filtros: dict[str, Any] | None = None,
        pagina: int = 1,
        limite: int = 50,
    ) -> ResultadoPagosDTO:
        filtros = filtros or {}
        pagina_segura = max(1, pagina)
        limite_seguro = max(1, limite)
        texto_filtro = str(filtros.get("texto") or "").strip()
        condiciones = [
            "(:texto = '' OR p.folio ILIKE :patron OR u.codigo ILIKE :patron "
            "OR p.residente_nombre ILIKE :patron)"
        ]
        params: dict[str, Any] = {
            "texto": texto_filtro,
            "patron": f"%{texto_filtro}%",
            "limite": limite_seguro,
            "offset": (pagina_segura - 1) * limite_seguro,
        }
        for key, column in (("metodo", "p.metodo_pago"), ("estado", "p.estado")):
            value = str(filtros.get(key) or "").strip()
            if value:
                condiciones.append(f"{column}::text ILIKE :{key}")
                params[key] = f"%{value}%"
        for key, operator in (("fecha_desde", ">="), ("fecha_hasta", "<=")):
            fecha_value = filtros.get(key)
            if fecha_value:
                condiciones.append(f"p.fecha {operator} :{key}")
                params[key] = fecha_value

        where = " AND ".join(condiciones)
        with self._session_factory() as session:
            total = session.execute(
                text(
                    "SELECT count(*) FROM pagos p JOIN unidades u ON u.id = p.unidad_id "
                    f"WHERE {where}"
                ),
                params,
            ).scalar_one()
            rows = session.execute(
                text(f"""
                    SELECT p.id, p.folio, p.fecha, u.codigo AS unidad,
                           p.residente_nombre AS pagador, p.monto,
                           p.metodo_pago AS metodo, p.estado::text AS estado,
                           p.referencia
                    FROM pagos p JOIN unidades u ON u.id = p.unidad_id
                    WHERE {where}
                    ORDER BY p.fecha DESC, p.folio DESC
                    LIMIT :limite OFFSET :offset
                """),
                params,
            ).fetchall()

        filas = [
            PagoListadoDTO(
                pago_id=row.id,
                folio=row.folio,
                fecha=row.fecha,
                unidad=row.unidad,
                pagador=row.pagador,
                monto=Decimal(str(row.monto)),
                metodo=row.metodo,
                estado=str(row.estado),
                referencia=row.referencia,
            )
            for row in rows
        ]
        return ResultadoPagosDTO(
            filas=filas,
            total_paginas=(total + limite_seguro - 1) // limite_seguro if total else 0,
        )
