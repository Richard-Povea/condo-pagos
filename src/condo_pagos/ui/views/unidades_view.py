from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QSplitter,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from condo_pagos.ui.components.base import Tarjeta
from condo_pagos.ui.components.tabla_unidades import UnidadesTableModel


class UnidadesView(QWidget):
    def __init__(self, vm, parent=None) -> None:
        super().__init__(parent)
        self._vm = vm
        self._inicializar_ui()
        self._conectar_signals()
        
        # Carga inicial
        self._vm.cargar_unidades()

    def _inicializar_ui(self) -> None:
        layout_principal = QVBoxLayout(self)
        layout_principal.setContentsMargins(24, 24, 24, 24)
        layout_principal.setSpacing(16)

        # Título y Filtros Superiores
        layout_top = QHBoxLayout()
        lbl_titulo = QLabel("Unidades y Estado de Cuenta")
        lbl_titulo.setStyleSheet("font-size: 18pt; font-weight: bold;")
        
        self.chk_morosas = QCheckBox("Solo unidades con deuda")
        
        layout_top.addWidget(lbl_titulo)
        layout_top.addStretch()
        layout_top.addWidget(self.chk_morosas)
        layout_principal.addLayout(layout_top)

        # Splitter principal: Izquierda (Tabla), Derecha (Detalle / Estado de cuenta)
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # --- PANEL IZQUIERDO: Tabla de Unidades ---
        w_izq = QWidget()
        v_izq = QVBoxLayout(w_izq)
        v_izq.setContentsMargins(0, 0, 0, 0)

        self.txt_buscar = QLineEdit()
        self.txt_buscar.setPlaceholderText("Filtrar por unidad o responsable…")
        v_izq.addWidget(self.txt_buscar)

        self.tabla_unidades = QTableView()
        self.tabla_unidades.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.tabla_unidades.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self.tabla_unidades.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        v_izq.addWidget(self.tabla_unidades)

        splitter.addWidget(w_izq)

        # --- PANEL DERECHO: Detalle de Unidad seleccionada ---
        self.card_detalle = Tarjeta("Detalle de Unidad")
        self.lbl_info_detalle = QLabel(
            "Seleccione una unidad para ver su estado de cuenta y cargos pendientes."
            )
        self.lbl_info_detalle.setStyleSheet("color: #6B7785;")
        self.card_detalle.agregar_widget(self.lbl_info_detalle)

        self.btn_ir_pago = QPushButton("Registrar pago a esta unidad")
        self.btn_ir_pago.setProperty("variant", "primary")
        self.btn_ir_pago.setEnabled(False)
        self.card_detalle.agregar_widget(self.btn_ir_pago)

        splitter.addWidget(self.card_detalle)
        splitter.setSizes([600, 400])

        layout_principal.addWidget(splitter)

    def _conectar_signals(self) -> None:
        self.chk_morosas.toggled.connect(self._vm.alternar_filtro_morosas)
        self._vm.unidades_cargadas.connect(self._actualizar_tabla)

    def _actualizar_tabla(self, unidades: list) -> None:
        modelo = UnidadesTableModel(unidades)
        self.tabla_unidades.setModel(modelo)