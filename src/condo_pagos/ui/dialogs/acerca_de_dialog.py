from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QWidget

class AcercaDeDialog(QDialog):
    def __init__(self, version_app: str = "1.0.0", schema_version: str = "2026.09.v1", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Acerca de CondoPagos")
        self.resize(350, 220)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        lbl_titulo = QLabel("<b>Módulo de Pagos - Condominios</b>")
        lbl_titulo.setStyleSheet("font-size: 14pt;")
        
        layout.addWidget(lbl_titulo)
        layout.addWidget(QLabel(f"Versión de la aplicación: {version_app}"))
        layout.addWidget(QLabel(f"Versión del esquema de BD (schema_info): {schema_version}"))
        layout.addWidget(QLabel("Desarrollado bajo arquitectura limpia y PyQt6."))

        layout.addStretch()
        btn_cerrar = QPushButton("Cerrar")
        btn_cerrar.clicked.connect(self.accept)
        layout.addWidget(btn_cerrar)