from PySide6.QtCore import Qt
from PySide6.QtGui import QFocusEvent
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from condo_pagos.ui.theme.tokens import (
    COLOR_DANGER,
    COLOR_SECONDARY,
    COLOR_SUCCESS,
    COLOR_WARNING,
)


class Tarjeta(QFrame):
    def __init__(self, titulo: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setProperty("card", "true")
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(16, 16, 16, 16)
        self._layout.setSpacing(8)

        if titulo:
            lbl_titulo = QLabel(titulo)
            lbl_titulo.setStyleSheet("font-weight: bold; font-size: 11pt;")
            self._layout.addWidget(lbl_titulo)

    def agregar_widget(self, widget: QWidget) -> None:
        self._layout.addWidget(widget)


class CampoMonto(QLineEdit):
    """Campo de texto especializado que acepta montos monetarios formateados."""
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setPlaceholderText("$ 0")

    def focusOutEvent(self, event: QFocusEvent) -> None:
        super().focusOutEvent(event)
        # Aquí se aplicará el formateo visual al perder el foco en siguientes iteraciones


class ChipEstado(QLabel):
    """Chip visual para mostrar estados con color y texto explícito."""
    def __init__(self, estado: str, parent: QWidget | None = None) -> None:
        super().__init__(estado, parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet(self._estilo_para_estado(estado))
        self.setFixedSize(80, 24)

    def _estilo_para_estado(self, estado: str) -> str:
        estilos_base = "border-radius: 4px; font-weight: bold; font-size: 9pt; color: white;"
        e = estado.lower()
        if "pagado" in e:
            return f"{estilos_base} background-color: {COLOR_SUCCESS};"
        elif "parcial" in e:
            return f"{estilos_base} background-color: {COLOR_WARNING};"
        elif "anulado" in e or "peligro" in e:
            return f"{estilos_base} background-color: {COLOR_DANGER};"
        else:
            return f"{estilos_base} background-color: {COLOR_SECONDARY};"