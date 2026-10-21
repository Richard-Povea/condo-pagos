from collections.abc import Callable
from typing import Any

from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QWidget,
    QVBoxLayout,
)


class VerificarComprobanteDialog(QDialog):
    def __init__(self, verificar_comprobante_uc: Callable[[str], Any], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Verificar Comprobante de Pago")
        self.resize(450, 300)
        self._verificar_uc = verificar_comprobante_uc
        self._inicializar_ui()

    def _inicializar_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        layout.addWidget(QLabel("Ingrese el folio del comprobante o código de validación QR:"))
        
        layout_input = QHBoxLayout()
        self.txt_codigo = QLineEdit()
        self.txt_codigo.setPlaceholderText("Ej: PAGO-000123 o código QR...")
        self.btn_verificar = QPushButton("Verificar")
        self.btn_verificar.setProperty("variant", "primary")
        
        layout_input.addWidget(self.txt_codigo)
        layout_input.addWidget(self.btn_verificar)
        layout.addLayout(layout_input)

        # Resultado de la verificación
        self.lbl_resultado = QLabel("")
        self.lbl_resultado.setWordWrap(True)
        self.lbl_resultado.setStyleSheet("font-size: 11pt; padding: 8px; border-radius: 4px;")
        layout.addWidget(self.lbl_resultado)

        layout.addStretch()
        
        # Conexiones
        self.btn_verificar.clicked.connect(self._ejecutar_verificacion)

    def _ejecutar_verificacion(self) -> None:
        codigo = self.txt_codigo.text().strip()
        if not codigo:
            return

        try:
            resultado = self._verificar_uc(codigo)
            if resultado and getattr(resultado, "valido", False):
                self.lbl_resultado.setStyleSheet(
                    "background-color: #E3FCEF; color: #006644; font-weight: bold;"
                    )
                self.lbl_resultado.setText(
                    f"✔ COMPROBANTE VÁLIDO<br>"
                    f"• Folio: {resultado.folio}<br>"
                    f"• Fecha: {resultado.fecha}<br>"
                    f"• Unidad: {resultado.unidad}<br>"
                    f"• Monto: ${resultado.monto:,.0f}"
                )
            else:
                self.lbl_resultado.setStyleSheet(
                    "background-color: #FFEBE6; color: #DE350B; font-weight: bold;"
                    )
                self.lbl_resultado.setText(
                    "✖ NO COINCIDE: El comprobante no existe o no es válido."
                    )
        except Exception:
            self.lbl_resultado.setStyleSheet(
                "background-color: #FFEBE6; color: #DE350B; font-weight: bold;"
                )
            self.lbl_resultado.setText(
                "✖ Error al verificar el comprobante en el sistema."
                )