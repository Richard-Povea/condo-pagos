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
        self._unidades = []
        self._unidad_seleccionada = None
        self._inicializar_ui()
        self._conectar_signals()

        # Carga inicial
        self._vm.cargar_unidades()

    def _inicializar_ui(self) -> None:
        layout_principal = QVBoxLayout(self)
        layout_principal.setContentsMargins(24, 24, 24, 24)
        layout_principal.setSpacing(16)

        layout_top = QHBoxLayout()
        lbl_titulo = QLabel("Unidades y Estado de Cuenta")
        lbl_titulo.setStyleSheet("font-size: 18pt; font-weight: bold;")

        self.chk_morosas = QCheckBox("Solo unidades con deuda")

        layout_top.addWidget(lbl_titulo)
        layout_top.addStretch()
        layout_top.addWidget(self.chk_morosas)
        layout_principal.addLayout(layout_top)

        splitter = QSplitter(Qt.Orientation.Horizontal)

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
        self.txt_buscar.textChanged.connect(self._filtrar_unidades)
        self.tabla_unidades.clicked.connect(self._seleccionar_fila)
        self.btn_ir_pago.clicked.connect(self._ir_a_registrar_pago)
        self._vm.unidades_cargadas.connect(self._actualizar_tabla)
        self._vm.detalle_unidad_cargado.connect(self._mostrar_estado_cuenta)
        self._vm.error.connect(self._mostrar_error)

    def _actualizar_tabla(self, unidades: list) -> None:
        self._unidades = list(unidades)
        self._unidades_visibles = list(unidades)
        self._unidad_seleccionada = None
        self.btn_ir_pago.setEnabled(False)
        modelo = UnidadesTableModel(self._unidades)
        self.tabla_unidades.setModel(modelo)
        self.lbl_info_detalle.setText(
            "Seleccione una unidad para ver su estado de cuenta y cargos pendientes."
        )

    def _filtrar_unidades(self, texto: str) -> None:
        criterio = texto.casefold().strip()
        unidades = [
            u for u in self._unidades
            if criterio in u.identificador.casefold()
            or criterio in u.responsable.casefold()
            or criterio in u.rut.casefold()
        ]
        modelo = UnidadesTableModel(unidades)
        self.tabla_unidades.setModel(modelo)
        # Mantener el mapeo de filas sincronizado con el modelo filtrado.
        self._unidades_visibles = unidades

    def _seleccionar_fila(self, index) -> None:
        unidades = getattr(self, "_unidades_visibles", self._unidades)
        fila = index.row()
        if fila < 0 or fila >= len(unidades):
            return
        self._unidad_seleccionada = unidades[fila]
        self.btn_ir_pago.setEnabled(True)
        self.lbl_info_detalle.setText(
            f"Unidad {self._unidad_seleccionada.identificador} — "
            f"{self._unidad_seleccionada.responsable}\nConsultando estado de cuenta…"
        )
        self._vm.seleccionar_unidad(str(self._unidad_seleccionada.unidad_id))

    def _mostrar_estado_cuenta(self, estado) -> None:
        if estado is None or self._unidad_seleccionada is None:
            return
        saldo = getattr(estado, "total_adeudado", self._unidad_seleccionada.saldo_total)
        self.lbl_info_detalle.setText(
            f"Unidad {self._unidad_seleccionada.identificador}\n"
            f"Responsable: {self._unidad_seleccionada.responsable}\n"
            f"Saldo pendiente: $ {saldo:,.0f}"
        )

    def _mostrar_error(self, mensaje: str) -> None:
        self.lbl_info_detalle.setText(f"No se pudo cargar el detalle: {mensaje}")

    def _ir_a_registrar_pago(self) -> None:
        if self._unidad_seleccionada is not None:
            self._vm.iniciar_pago_para_unidad(self._unidad_seleccionada)
