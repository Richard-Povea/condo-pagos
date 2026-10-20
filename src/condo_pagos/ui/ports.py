"""Contratos del backend consumidos por la capa de interfaz.

Los contratos describen las operaciones que necesita la UI, no su implementación.
Tanto el contenedor demo como el contenedor PostgreSQL deben satisfacerlos.
"""

from datetime import date
from decimal import Decimal
from typing import Any, Protocol
from uuid import UUID


class UiContainer(Protocol):
    nombre_condominio: str

    def listar_unidades(self, solo_morosas: bool = False) -> list[Any]: ...
    def buscar_unidades(self, texto: str = "") -> list[Any]: ...
    def consultar_estado_cuenta(self, unidad_id: UUID | str) -> Any: ...
    def registrar_pago(
        self, *, unidad_id: UUID | str, monto: Decimal | int | str,
        metodo_pago: str = "EFECTIVO", referencia: str = "",
        operador: str = "", fecha: date | None = None,
    ) -> Any: ...
    def listar_pagos(
        self, *, filtros: dict[str, Any] | None = None,
        pagina: int = 1, limite: int = 50,
    ) -> Any: ...
    def emitir_pdf(self, comprobante_id: str) -> str: ...
    def anular_pago(
        self, *, pago_id: str, motivo: str = "", operador: str = "",
    ) -> str: ...
