from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from condo_pagos.ui.components.tabla_pagos import PagosTableModel


class PagosView(QWidget):
    def __init__(self, vm, parent=None) -> None:
        super().__init__(parent)
        self._vm = vm
        self._inicializar_ui()
        self._conectar_signals()

        # Carga inicial
        self._vm.cargar_pagos()

    def _inicializar_ui(self) -> None:
        layout_principal = QVBoxLayout(self)
        layout_principal.setContentsMargins(24, 24, 24, 24)
        layout_principal.setSpacing(16)

        layout_top = QHBoxLayout()
        lbl_titulo = QLabel("Historial de Pagos y Comprobantes")
        lbl_titulo.setStyleSheet("font-size: 18pt; font-weight: bold;")

        self.txt_buscar = QLineEdit()
        self.txt_buscar.setPlaceholderText("Buscar por folio, unidad o pagador…")

        layout_top.addWidget(lbl_titulo)
        layout_top.addStretch()
        layout_top.addWidget(self.txt_buscar)
        layout_principal.addLayout(layout_top)

        self.tabla_pagos = QTableView()
        self.tabla_pagos.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.tabla_pagos.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self.tabla_pagos.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        layout_principal.addWidget(self.tabla_pagos)

        layout_acciones = QHBoxLayout()
        self.btn_reimprimir = QPushButton("Abrir / Reimprimir Comprobante")
        self.btn_anular = QPushButton("Anular pago seleccionado")
        self.btn_anular.setProperty("variant", "danger")

        layout_acciones.addWidget(self.btn_reimprimir)
        layout_acciones.addWidget(self.btn_anular)
        layout_acciones.addStretch()
        layout_principal.addLayout(layout_acciones)

    def _conectar_signals(self) -> None:
        self._vm.pagos_cargados.connect(self._actualizar_tabla)
        self.txt_buscar.textChanged.connect(self._filtrar_texto)
        self.btn_reimprimir.clicked.connect(self._abrir_comprobante_seleccionado)

    def _actualizar_tabla(self, pagos: list, total_paginas: int) -> None:
        modelo = PagosTableModel(pagos)
        self.tabla_pagos.setModel(modelo)

    def _filtrar_texto(self, texto: str) -> None:
        self._vm.filtro_texto = texto
        self._vm.pagina_actual = 1
        self._vm.cargar_pagos()

    def _abrir_comprobante_seleccionado(self) -> None:
        indice = self.tabla_pagos.selectionModel().currentIndex()
        if not indice.isValid():
            QMessageBox.information(
                self,
                "Seleccionar pago",
                "Selecciona un pago de la tabla para abrir su comprobante.",
            )
            return

        modelo = self.tabla_pagos.model()
        pagos = getattr(modelo, "_pagos_raw", [])
        if indice.row() >= len(pagos):
            QMessageBox.warning(
                self,
                "Comprobante no disponible",
                "No se pudo identificar el pago seleccionado.",
            )
            return

        pago = pagos[indice.row()]
        self._vm.abrir_o_reimprimir_comprobante(
            comprobante_id=str(pago.folio),
            ruta_actual_disco=None,
        )
