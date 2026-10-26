from collections.abc import Callable
from datetime import date
from decimal import Decimal
from typing import Any

from PySide6.QtCore import Signal

from condo_pagos.ui.viewmodels.base import BaseViewModel


class RegistrarPagoViewModel(BaseViewModel):
    # Señales hacia la vista
    estado_cuenta_cargado = Signal(object)  # Estado de cuenta DTO
    resultado_busqueda = Signal(list)       # Lista de unidades encontradas
    resumen_imputacion_listo = Signal(dict) # Desglose de distribución de pagos
    pago_registrado = Signal(str)           # Folio generado
    error_campo = Signal(str, str)          # (campo, mensaje)

    def __init__(
            self, 
            buscar_unidades_uc: Callable[..., Any],
            consultar_estado_uc: Callable[..., Any],
            registrar_pago_uc: Callable[..., Any], parent: Any | None = None) -> None:
        super().__init__(parent=parent)
        self._buscar_uc = buscar_unidades_uc
        self._consultar_estado_uc = consultar_estado_uc
        self._registrar_uc = registrar_pago_uc

        # Estado interno del formulario
        self.unidad_seleccionada: Any | None = None
        self.monto_actual: Decimal = Decimal("0")
        self.metodo_pago: str = "EFECTIVO"
        self.referencia: str = ""
        self.fecha_pago: date = date.today()
        
        # Control de versiones para búsquedas asíncronas desordenadas (debounce/stale)
        self._token_busqueda: int = 0

    def buscar_unidades(self, texto: str) -> None:
        """Busca unidades con control de obsolescencia de respuestas."""
        self._token_busqueda += 1
        token_actual = self._token_busqueda

        def tarea() -> Any:
            return self._buscar_uc(texto)

        def on_ok(res: Any) -> None:
            if token_actual == self._token_busqueda:
                self.resultado_busqueda.emit(res)

        self._ejecutar(tarea, on_ok=on_ok)

    def seleccionar_unidad(self, unidad: Any) -> None:
        self.unidad_seleccionada = unidad
        if not unidad:
            self.estado_cuenta_cargado.emit(None)
            return

        def tarea() -> Any:
            return self._consultar_estado_uc(unidad.unidad_id)

        self._ejecutar(tarea, on_ok=lambda estado: self.estado_cuenta_cargado.emit(estado))

    def validar_y_actualizar_monto(self, texto_monto: str, deuda_total: Decimal) -> None:
        """Validación en línea del monto ingresado."""
        limpio = texto_monto.replace("$", "").replace(".", "").strip()
        if not limpio:
            self.monto_actual = Decimal("0")
            return

        try:
            monto = Decimal(limpio)
            if monto <= 0:
                self.error_campo.emit("monto", "El monto debe ser mayor a 0.")
            elif monto > deuda_total:
                exceso = monto - deuda_total
                self.error_campo.emit(
                    "monto", 
                    f"El monto supera la deuda en ${exceso:,.0f}. Ajústelo o use Pagar todo.")
            else:
                self.monto_actual = monto
                self.error_campo.emit("monto", "")
        except Exception:
            self.error_campo.emit("monto", "Formato de monto inválido.")

    def registrar_pago(self, operador: str) -> None:
        """Ejecuta el caso de uso de registro de pago de forma segura y atómica."""
        if not self.unidad_seleccionada or self.monto_actual <= 0:
            return

        def tarea() -> Any:
            # Comando hacia el backend
            return self._registrar_uc(
                unidad_id=self.unidad_seleccionada.unidad_id, # type:ignore
                monto=self.monto_actual,
                metodo_pago=self.metodo_pago,
                referencia=self.referencia,
                operador=operador,
                fecha=self.fecha_pago
            )

        def on_ok(resultado: Any) -> None:
            self.pago_registrado.emit(resultado.folio)

        self._ejecutar(tarea, on_ok=on_ok)