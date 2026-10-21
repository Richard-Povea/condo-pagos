from decimal import Decimal
from typing import Any

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from condo_pagos.ui.components.base import CampoMonto, Tarjeta


class RegistrarPagoView(QWidget):
    def __init__(self, vm: Any, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._vm = vm
        self._unidades_encontradas: list[Any] = []
        self._deuda_total = Decimal("0")
        self._inicializar_ui()
        self._conectar_signals()

    def _inicializar_ui(self) -> None:
        layout_principal = QVBoxLayout(self)
        layout_principal.setContentsMargins(24, 24, 24, 24)
        layout_principal.setSpacing(16)

        lbl_titulo = QLabel("Registrar pago")
        lbl_titulo.setStyleSheet("font-size: 18pt; font-weight: bold;")
        layout_principal.addWidget(lbl_titulo)

        card_unidad = Tarjeta("1. Unidad")
        self.txt_buscar = QLineEdit()
        self.txt_buscar.setPlaceholderText("Buscar por unidad, nombre o RUT…")
        card_unidad.agregar_widget(self.txt_buscar)

        self.combo_unidades = QComboBox()
        self.combo_unidades.setPlaceholderText("Seleccione una unidad")
        card_unidad.agregar_widget(self.combo_unidades)

        layout_unidad_info = QHBoxLayout()
        self.lbl_detalle_unidad = QLabel("Seleccione una unidad para ver el estado de cuenta.")
        self.lbl_detalle_unidad.setStyleSheet("color: #6B7785;")
        self.lbl_deuda_total = QLabel("Deuda total: $ 0")
        self.lbl_deuda_total.setStyleSheet(
            "font-weight: bold; font-size: 12pt; color: #1F3A5F;"
        )
        layout_unidad_info.addWidget(self.lbl_detalle_unidad)
        layout_unidad_info.addStretch()
        layout_unidad_info.addWidget(self.lbl_deuda_total)
        w_unidad_info = QWidget()
        w_unidad_info.setLayout(layout_unidad_info)
        card_unidad.agregar_widget(w_unidad_info)
        layout_principal.addWidget(card_unidad)

        card_pago = Tarjeta("2. Datos del pago")
        layout_monto = QHBoxLayout()
        self.input_monto = CampoMonto()
        self.btn_pagar_todo = QPushButton("Pagar todo")
        self.btn_pagar_antiguo = QPushButton("Solo el más antiguo")
        self.combo_metodo = QComboBox()
        self.combo_metodo.addItems(["EFECTIVO", "TRANSFERENCIA", "WEBPAY"])
        layout_monto.addWidget(QLabel("Monto:"))
        layout_monto.addWidget(self.input_monto)
        layout_monto.addWidget(self.btn_pagar_todo)
        layout_monto.addWidget(self.btn_pagar_antiguo)
        card_pago.agregar_widget(self._widget_con_layout(layout_monto))
        layout_metodo = QHBoxLayout()
        layout_metodo.addWidget(QLabel("Método de pago:"))
        layout_metodo.addWidget(self.combo_metodo)
        layout_metodo.addStretch()
        card_pago.agregar_widget(self._widget_con_layout(layout_metodo))
        self.txt_referencia = QLineEdit()
        self.txt_referencia.setPlaceholderText("Referencia (opcional; ej. número de transferencia)")
        card_pago.agregar_widget(self.txt_referencia)
        layout_principal.addWidget(card_pago)

        layout_acciones = QHBoxLayout()
        layout_acciones.addStretch()
        self.btn_cancelar = QPushButton("Cancelar")
        self.btn_registrar = QPushButton("Registrar pago")
        self.btn_registrar.setProperty("variant", "primary")
        self.btn_registrar.setEnabled(False)
        layout_acciones.addWidget(self.btn_cancelar)
        layout_acciones.addWidget(self.btn_registrar)
        layout_principal.addLayout(layout_acciones)
        layout_principal.addStretch()

    @staticmethod
    def _widget_con_layout(layout: Any) -> QWidget:
        widget = QWidget()
        widget.setLayout(layout)
        return widget

    def _conectar_signals(self) -> None:
        self._timer_debounce = QTimer(self)
        self._timer_debounce.setSingleShot(True)
        self._timer_debounce.setInterval(250)
        self._timer_debounce.timeout.connect(
            lambda: self._vm.buscar_unidades(self.txt_buscar.text())
        )
        self.txt_buscar.textChanged.connect(self._timer_debounce.start)
        self.combo_unidades.currentIndexChanged.connect(self._unidad_combo_cambiada)
        self.btn_pagar_todo.clicked.connect(self._pagar_todo)
        self.btn_pagar_antiguo.clicked.connect(self._pagar_monto_disponible)
        self.input_monto.textChanged.connect(self._validar_monto)
        self.combo_metodo.currentTextChanged.connect(self._actualizar_metodo)
        self.txt_referencia.textChanged.connect(self._actualizar_referencia)
        self.btn_registrar.clicked.connect(self._registrar_pago)
        self.btn_cancelar.clicked.connect(self._cancelar)

        self._vm.resultado_busqueda.connect(self._mostrar_resultados)
        self._vm.ocupado_cambio.connect(self._manejar_ocupado)
        self._vm.error.connect(self._mostrar_error)
        self._vm.estado_cuenta_cargado.connect(self._mostrar_estado_cuenta)
        self._vm.pago_registrado.connect(self._pago_registrado)

    def al_mostrar(self, parametros: Any | None = None) -> None:
        if parametros is not None:
            self._vm.seleccionar_unidad(parametros)
            self.lbl_detalle_unidad.setText(
                f"Unidad {getattr(parametros, 'identificador', '—')} — "
                f"{getattr(parametros, 'responsable', '')}"
            )
            self.lbl_deuda_total.setText("Deuda total: consultando…")
            self.btn_registrar.setEnabled(False)
        else:
            self._vm.buscar_unidades("")

    def _mostrar_resultados(self, unidades: list[Any]) -> None:
        self._unidades_encontradas = list(unidades)
        seleccion_id = getattr(self._vm.unidad_seleccionada, "unidad_id", None)
        self.combo_unidades.blockSignals(True)
        self.combo_unidades.clear()
        for unidad in unidades:
            self.combo_unidades.addItem(
                f"{unidad.identificador} — {unidad.responsable}",
                unidad,
            )
        if seleccion_id is not None:
            for i, unidad in enumerate(unidades):
                if unidad.unidad_id == seleccion_id:
                    self.combo_unidades.setCurrentIndex(i)
                    break
        self.combo_unidades.blockSignals(False)

    def _unidad_combo_cambiada(self, indice: int) -> None:
        unidad = self.combo_unidades.itemData(indice)
        if unidad is not None:
            self._vm.seleccionar_unidad(unidad)
            self.lbl_detalle_unidad.setText(
                f"Unidad {unidad.identificador} — {unidad.responsable}"
            )

    def _mostrar_estado_cuenta(self, estado: Any | None) -> None:
        if estado is None:
            self._deuda_total = Decimal("0")
            self.lbl_deuda_total.setText("Deuda total: $ 0")
            self.btn_registrar.setEnabled(False)
            return
        self._deuda_total = Decimal(str(getattr(
            estado, "total_adeudado", getattr(estado, "saldo_total", 0)
        )))
        self.lbl_deuda_total.setText(f"Deuda total: $ {self._deuda_total:,.0f}")
        self._validar_monto()

    def _pagar_todo(self) -> None:
        self.input_monto.setText(str(int(self._deuda_total)))
        self._validar_monto()

    def _pagar_monto_disponible(self) -> None:
        # El contenedor demo no modela cargos individuales; se ofrece el saldo total.
        self._pagar_todo()

    def _validar_monto(self, *_args) -> None:
        limpio = self.input_monto.text().replace("$", "").replace(".", "").replace(",", "").strip()
        try:
            monto = Decimal(limpio) if limpio else Decimal("0")
        except Exception:
            monto = Decimal("0")
        valido = (
            self._vm.unidad_seleccionada is not None
            and monto > 0
            and monto <= self._deuda_total
            and not self._vm.ocupado
        )
        self.btn_registrar.setEnabled(valido)
        if monto > self._deuda_total and self._deuda_total > 0:
            self.lbl_detalle_unidad.setText("El monto ingresado supera la deuda pendiente.")

    def _actualizar_metodo(self, metodo: str) -> None:
        self._vm.metodo_pago = metodo

    def _actualizar_referencia(self, referencia: str) -> None:
        self._vm.referencia = referencia.strip()

    def _registrar_pago(self) -> None:
        limpio = self.input_monto.text().replace("$", "").replace(".", "").replace(",", "").strip()
        try:
            monto = Decimal(limpio)
        except Exception:
            QMessageBox.warning(self, "Monto inválido", "Ingresa un monto válido.")
            return
        self._vm.monto_actual = monto
        self._vm.metodo_pago = self.combo_metodo.currentText()
        self._vm.referencia = self.txt_referencia.text().strip()
        self._vm.registrar_pago(operador="Demo")

    def _pago_registrado(self, folio: str) -> None:
        # Actualizar el saldo de la unidad seleccionada después de guardar el pago.
        unidad = self._vm.unidad_seleccionada
        self.input_monto.clear()
        self.txt_referencia.clear()
        self.btn_registrar.setEnabled(False)
        if unidad is not None:
            self.lbl_deuda_total.setText("Deuda total: actualizando…")
            self._vm.seleccionar_unidad(unidad)
        self._vm.buscar_unidades("")
        QMessageBox.information(
            self, "Pago registrado", f"El pago se registró correctamente. Folio: {folio}"
        )

    def _mostrar_error(self, mensaje: str) -> None:
        QMessageBox.critical(self, "Error", mensaje)

    def _manejar_ocupado(self, ocupado: bool) -> None:
        self.btn_registrar.setEnabled(
            not ocupado
            and self._vm.unidad_seleccionada is not None
            and self._deuda_total > 0
        )

    def _cancelar(self) -> None:
        self.input_monto.clear()
        self.txt_referencia.clear()
        self._vm.seleccionar_unidad(None)
