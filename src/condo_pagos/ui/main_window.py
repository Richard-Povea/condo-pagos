from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from condo_pagos.ui.theme.tokens import COLOR_PRIMARY, COLOR_SURFACE


class MainWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Gestión de Condominios - Pagos")
        self.setMinimumSize(960, 640)
        
        self.settings = QSettings("CondoPagos", "ModuloPagos")
        self._inicializar_ui()
        self._restaurar_geometria()

    def _inicializar_ui(self) -> None:
        layout_principal = QHBoxLayout(self)
        layout_principal.setContentsMargins(0, 0, 0, 0)
        layout_principal.setSpacing(0)

        # 1. Barra Lateral (Sidebar de 220px)
        sidebar = QFrame()
        sidebar.setFixedWidth(220)
        sidebar.setStyleSheet(
            f"background-color: {COLOR_SURFACE}; border-right: 1px solid #E1E6EC;"
            )
        
        layout_sidebar = QVBoxLayout(sidebar)
        layout_sidebar.setContentsMargins(16, 24, 16, 24)
        layout_sidebar.setSpacing(12)

        lbl_condominio = QLabel("Los Alerces")
        lbl_condominio.setStyleSheet(
            f"font-size: 14pt; font-weight: bold; color: {COLOR_PRIMARY};"
            )
        layout_sidebar.addWidget(lbl_condominio)
        layout_sidebar.addSpacing(16)

        # Botones de Navegación
        self.btn_registrar = QPushButton("Registrar pago")
        self.btn_registrar.setProperty("variant", "text")
        self.btn_unidades = QPushButton("Unidades")
        self.btn_unidades.setProperty("variant", "text")
        self.btn_pagos = QPushButton("Pagos")
        self.btn_pagos.setProperty("variant", "text")
        self.btn_config = QPushButton("Configuración")
        self.btn_config.setProperty("variant", "text")

        for btn in [
            self.btn_registrar, 
            self.btn_unidades, 
            self.btn_pagos, 
            self.btn_config]:
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            layout_sidebar.addWidget(btn)

        layout_sidebar.addStretch()
        layout_principal.addWidget(sidebar)

        # 2. Contenido Central (QStackedWidget)
        self.stack = QStackedWidget()
        
        # Vistas temporales de marcador de posición
        vista_registrar = QWidget()
        self.stack.addWidget(vista_registrar) # Índice 0: Registrar Pago
        
        layout_principal.addWidget(self.stack)

        # Conexiones de navegación
        self.btn_registrar.clicked.connect(lambda: self.stack.setCurrentIndex(0))

    def _restaurar_geometria(self) -> None:
        geometria = self.settings.value("geometry")
        if geometria:
            self.restoreGeometry(geometria)

    def closeEvent(self, event: QCloseEvent) -> None:
        self.settings.setValue("geometry", self.saveGeometry())
        super().closeEvent(event)