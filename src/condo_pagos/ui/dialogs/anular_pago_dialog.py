from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)


class AnularPagoDialog(QDialog):
    def __init__(self, folio: str, monto_str: str, unidad: str, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Anular Pago - {folio}")
        self.resize(400, 300)
        self.motivo: str = ""
        self._inicializar_ui(folio, monto_str, unidad)

    def _inicializar_ui(self, folio: str, monto_str: str, unidad: str) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Advertencia y resumen
        lbl_aviso = QLabel(f"<b>Advertencia:</b> Está a punto de anular el pago <b>{folio}</b>.")
        lbl_resumen = QLabel(
            f"• <b>Unidad:</b> {unidad}<br>"
            f"• <b>Monto a revertir:</b> {monto_str}<br>"
            f"Esta acción revertirá los cargos imputados y actualizará el saldo de la unidad."
        )
        layout.addWidget(lbl_aviso)
        layout.addWidget(lbl_resumen)

        # Campo de motivo obligatorio
        layout.addWidget(QLabel("Motivo de anulación (mínimo 10 caracteres): *"))
        self.txt_motivo = QTextEdit()
        self.txt_motivo.setPlaceholderText("Explique detalladamente el motivo de la anulación...")
        layout.addWidget(self.txt_motivo)

        # Botones de acción
        layout_botones = QHBoxLayout()
        layout_botones.addStretch()

        self.btn_cancelar = QPushButton("Cancelar")
        self.btn_anular = QPushButton("Anular pago")
        self.btn_anular.setProperty("variant", "danger")
        self.btn_anular.setEnabled(False)  # Deshabilitado hasta cumplir los 10 caracteres

        layout_botones.addWidget(self.btn_cancelar)
        layout_botones.addWidget(self.btn_anular)
        layout.addLayout(layout_botones)

        # Conexiones
        self.btn_cancelar.clicked.connect(self.reject)
        self.btn_anular.clicked.connect(self._aceptar_anulacion)
        self.txt_motivo.textChanged.connect(self._validar_motivo)

    def _validar_motivo(self) -> None:
        texto = self.txt_motivo.toPlainText().strip()
        valido = len(texto) >= 10
        self.btn_anular.setEnabled(valido)

    def _aceptar_anulacion(self) -> None:
        self.motivo = self.txt_motivo.toPlainText().strip()
        self.accept()