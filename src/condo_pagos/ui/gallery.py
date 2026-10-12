import sys

from PySide6.QtWidgets import QApplication, QLabel, QScrollArea, QVBoxLayout, QWidget

from condo_pagos.ui.components.base import CampoMonto, ChipEstado, Tarjeta
from condo_pagos.ui.theme.theme import generar_qss


class GaleriaComponentes(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Galería de Componentes - UI Condominios")
        self.resize(600, 700)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        contenedor = QWidget()
        layout = QVBoxLayout(contenedor)
        layout.setSpacing(16)

        # Título
        lbl = QLabel("Galería de Componentes del Sistema de Diseño")
        lbl.setStyleSheet("font-size: 14pt; font-weight: bold;")
        layout.addWidget(lbl)

        # 1. Tarjetas
        tarjeta = Tarjeta("Ejemplo de Tarjeta con Contenedor")
        tarjeta.agregar_widget(QLabel("Contenido interno de la tarjeta con esquinas de 8px."))
        layout.addWidget(tarjeta)

        # 2. Chips de Estado
        layout.addWidget(QLabel("Chips de Estado:"))
        layout.addWidget(ChipEstado("Pagado"))
        layout.addWidget(ChipEstado("Parcial"))
        layout.addWidget(ChipEstado("Anulado"))

        # 3. Campos Especializados
        layout.addWidget(QLabel("Campo de Monto:"))
        layout.addWidget(CampoMonto())

        scroll.setWidget(contenedor)
        v_main = QVBoxLayout(self)
        v_main.addWidget(scroll)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(generar_qss())
    galeria = GaleriaComponentes()
    galeria.show()
    sys.exit(app.exec())