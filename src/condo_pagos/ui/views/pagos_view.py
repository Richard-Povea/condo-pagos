from typing import Any

from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
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
    def __init__(self, vm: Any, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._vm = vm
        self._inicializar_ui()
        self._conectar_signals()
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
        self._vm.pago_anulado.connect(self._confirmar_anulacion_completada)
        self._vm.error.connect(self._mostrar_error)
        self.txt_buscar.textChanged.connect(self._filtrar_texto)
        self.btn_reimprimir.clicked.connect(self._abrir_comprobante_seleccionado)
        self.btn_anular.clicked.connect(self._anular_pago_seleccionado)

    def _actualizar_tabla(self, pagos: list[Any], total_paginas: int) -> None:
        self.tabla_pagos.setModel(PagosTableModel(pagos))

    def _filtrar_texto(self, texto: str) -> None:
        self._vm.filtro_texto = texto
        self._vm.pagina_actual = 1
        self._vm.cargar_pagos()

    def _pago_seleccionado(self) -> Any | None:
        selection = self.tabla_pagos.selectionModel()
        if selection is None:
            return None
        indice = selection.currentIndex()
        if not indice.isValid():
            return None
        pagos = getattr(self.tabla_pagos.model(), "_pagos_raw", [])
        if indice.row() >= len(pagos):
            return None
        return pagos[indice.row()]

    def _abrir_comprobante_seleccionado(self) -> None:
        pago = self._pago_seleccionado()
        if pago is None:
            QMessageBox.information(
                self, "Seleccionar pago",
                "Selecciona un pago de la tabla para abrir su comprobante.",
            )
            return
        self._vm.abrir_o_reimprimir_comprobante(
            comprobante_id=str(pago.folio),
            ruta_actual_disco=None,
        )

    def _anular_pago_seleccionado(self) -> None:
        pago = self._pago_seleccionado()
        if pago is None:
            QMessageBox.information(
                self, "Seleccionar pago",
                "Selecciona un pago de la tabla para anularlo.",
            )
            return
        if str(pago.estado).lower() == "anulado":
            QMessageBox.information(
                self, "Pago ya anulado", "El pago seleccionado ya está anulado."
            )
            return

        motivo, aceptado = QInputDialog.getMultiLineText(
            self,
            "Motivo de anulación",
            f"Indica el motivo para anular el pago {pago.folio} (mínimo 10 caracteres):",
        )
        if not aceptado:
            return
        if len(motivo.strip()) < 10:
            QMessageBox.warning(
                self, "Motivo insuficiente",
                "El motivo debe tener al menos 10 caracteres.",
            )
            return

        confirmar = QMessageBox.question(
            self,
            "Confirmar anulación",
            f"¿Confirmas anular el pago {pago.folio}? Esta acción restaurará los saldos asociados.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirmar != QMessageBox.StandardButton.Yes:
            return

        self._vm.anular_pago(
            pago_id=str(pago.pago_id),
            motivo=motivo.strip(),
            operador="Operador",
        )

    def _confirmar_anulacion_completada(self, folio: str) -> None:
        QMessageBox.information(
            self, "Pago anulado", f"El pago {folio} fue anulado correctamente."
        )

    def _mostrar_error(self, mensaje: str) -> None:
        QMessageBox.critical(self, "Error en pagos", mensaje)
