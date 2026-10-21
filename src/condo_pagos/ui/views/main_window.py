# src/condo_pagos/ui/views/main_window.py
from collections.abc import Callable
from typing import Any
from PySide6.QtCore import QSettings
from PySide6.QtGui import QCloseEvent, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)
from condo_pagos.ui.services.navegacion import ServicioNavegacion
from condo_pagos.ui import strings


class MainWindow(QMainWindow):
    def __init__(
        self,
        nav: ServicioNavegacion,
        paginas: dict[str, tuple[str, QWidget]],  # clave -> (titulo en menú, widget)
        nombre_condominio: str,
        hay_operaciones_en_curso: Callable[[], bool],
        esperar_trabajos: Callable[[], None],
    ) -> None:
        super().__init__()
        self._paginas = {k: w for k, (_, w) in paginas.items()}
        self._hay_ops, self._esperar = hay_operaciones_en_curso, esperar_trabajos
        self.setWindowTitle(getattr(strings, "APP_TITULO", "CondoPagos"))
        self.setMinimumSize(960, 640)

        # Barra lateral (Sidebar de 220 px)
        lateral = QWidget()
        lateral.setObjectName("Sidebar")
        lateral.setFixedWidth(220)
        lv = QVBoxLayout(lateral)
        lv.setContentsMargins(12, 24, 12, 24)
        lv.setSpacing(8)

        lbl_titulo_condo = QLabel(nombre_condominio)
        lbl_titulo_condo.setObjectName("SidebarTitulo")
        lbl_titulo_condo.setStyleSheet("font-weight: bold; font-size: 12pt; margin-bottom: 12px;")
        lv.addWidget(lbl_titulo_condo)

        self._grupo = QButtonGroup(self)
        self._grupo.setExclusive(True)
        self._botones: dict[str, QPushButton] = {}

        for i, (clave, (titulo, _)) in enumerate(paginas.items(), start=1):
            b = QPushButton(titulo)
            b.setCheckable(True)
            b.setProperty("variant", "nav")
            b.clicked.connect(lambda _=False, c=clave: nav.ir_a(c))
            self._grupo.addButton(b)
            self._botones[clave] = b
            lv.addWidget(b)
            
            # Atajos de teclado Ctrl+1, Ctrl+2, etc. corregidos
            shortcut = QShortcut(QKeySequence(f"Ctrl+{i}"), self)
            shortcut.activated.connect(lambda c=clave: nav.ir_a(c))

        lv.addStretch()

        # Contenido central con QStackedWidget
        self._stack = QStackedWidget()
        for w in self._paginas.values():
            self._stack.addWidget(w)

        central = QWidget()
        h = QHBoxLayout(central)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(0)
        h.addWidget(lateral)
        h.addWidget(self._stack, 1)
        self.setCentralWidget(central)

        # Suscripción a la navegación
        nav.navegar.connect(self._mostrar)
        self._restaurar_geometria()
        self._mostrar(next(iter(paginas)), None)

    def _mostrar(self, clave: str, parametros: Any | None) -> None:
        if clave not in self._paginas:
            return
        w = self._paginas[clave]
        self._stack.setCurrentWidget(w)
        if clave in self._botones:
            self._botones[clave].setChecked(True)
        
        # Cumple con el contrato Pagina si la vista implementa al_mostrar
        if hasattr(w, "al_mostrar"):
            w.al_mostrar(parametros)

    def closeEvent(self, e: QCloseEvent) -> None:
        if self._hay_ops():
            # Advertir si hay operaciones en curso
            e.ignore()
            return
        self._esperar()
        QSettings().setValue("ventana/geometria", self.saveGeometry())
        e.accept()

    def _restaurar_geometria(self) -> None:
        g = QSettings().value("ventana/geometria")
        if g:
            self.restoreGeometry(g)