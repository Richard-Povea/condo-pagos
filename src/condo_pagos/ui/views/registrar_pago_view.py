from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from condo_pagos.ui.components.base import CampoMonto, Tarjeta


class RegistrarPagoView(QWidget):
    def __init__(self, vm, parent=None) -> None:
        super().__init__(parent)
        self._vm = vm
        self._inicializar_ui()
        self._conectar_signals()

    def _inicializar_ui(self) -> None:
        layout_principal = QVBoxLayout(self)
        layout_principal.setContentsMargins(24, 24, 24, 24)
        layout_principal.setSpacing(16)

        # Título de la vista
        lbl_titulo = QLabel("Registrar pago")
        lbl_titulo.setStyleSheet("font-size: 18pt; font-weight: bold;")
        layout_principal.addWidget(lbl_titulo)

        # --- SECCIÓN 1: UNIDAD ---
        card_unidad = Tarjeta("1. Unidad")
        
        self.txt_buscar = QLineEdit()
        self.txt_buscar.setPlaceholderText("Buscar por unidad, nombre o RUT…")
        card_unidad.agregar_widget(self.txt_buscar)

        layout_unidad_info = QHBoxLayout()
        self.lbl_detalle_unidad = QLabel("Seleccione una unidad para ver el estado de cuenta.")
        self.lbl_detalle_unidad.setStyleSheet("color: #6B7785;")
        
        self.lbl_deuda_total = QLabel("Deuda total: $ 0")
        self.lbl_deuda_total.setStyleSheet("font-weight: bold; font-size: 12pt; color: #1F3A5F;")
        
        layout_unidad_info.addWidget(self.lbl_detalle_unidad)
        layout_unidad_info.addStretch()
        layout_unidad_info.addWidget(self.lbl_deuda_total)
        w_unidad_info = QWidget()
        w_unidad_info.setLayout(layout_unidad_info)
        card_unidad.agregar_widget(w_unidad_info)

        layout_principal.addWidget(card_unidad)

        # --- SECCIÓN 2: DATOS DEL PAGO ---
        card_pago = Tarjeta("2. Datos del pago")
        
        layout_monto = QHBoxLayout()
        self.input_monto = CampoMonto()
        self.btn_pagar_todo = QPushButton("Pagar todo")
        self.btn_pagar_antiguo = QPushButton("Solo el más antiguo")
        
        layout_monto.addWidget(QLabel("Monto:"))
        layout_monto.addWidget(self.input_monto)
        layout_monto.addWidget(self.btn_pagar_todo)
        layout_monto.addWidget(self.btn_pagar_antiguo)
        
        # Contenedor auxiliar para fila de monto
        w_monto = QWidget()
        w_monto.setLayout(layout_monto)
        card_pago.agregar_widget(w_monto)

        layout_principal.addWidget(card_pago)

        # --- SECCIÓN 3: ACCIONES FINALES ---
        layout_acciones = QHBoxLayout()
        layout_acciones.addStretch()
        
        self.btn_cancelar = QPushButton("Cancelar")
        self.btn_registrar = QPushButton("Registrar pago")
        self.btn_registrar.setProperty("variant", "primary")
        self.btn_registrar.setEnabled(False)  # Deshabilitado por defecto hasta que sea válido

        layout_acciones.addWidget(self.btn_cancelar)
        layout_acciones.addWidget(self.btn_registrar)
        layout_principal.addLayout(layout_acciones)

        layout_principal.addStretch()

    def _conectar_signals(self) -> None:
        # Búsqueda con temporizador debounce (250 ms)
        self._timer_debounce = QTimer()
        self._timer_debounce.setSingleShot(True)
        self._timer_debounce.setInterval(250)
        self._timer_debounce.timeout.connect(
            lambda: self._vm.buscar_unidades(self.txt_buscar.text())
            )

        self.txt_buscar.textChanged.connect(self._timer_debounce.start)

        # Conexiones con el ViewModel
        self._vm.ocupado_cambio.connect(self._manejar_ocupado)
        self._vm.error.connect(lambda msg: self.lbl_detalle_unidad.setText(f"Error: {msg}"))

    def _manejar_ocupado(self, ocupado: bool) -> None:
        # Bloquea el formulario durante operaciones asíncronas para evitar doble envío
        self.setEnabled(not ocupado)