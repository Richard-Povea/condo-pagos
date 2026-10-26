"""Inicialización de la aplicación Qt y su presentación visual.

Este módulo pertenece a la capa de interfaz: no selecciona ni construye
implementaciones de infraestructura. Esa responsabilidad está en
`condo_pagos.main`, el punto de composición de la aplicación.
"""

import logging
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from condo_pagos.ui.logging_config import configurar_logging
from condo_pagos.ui.theme.theme import generar_qss

log = logging.getLogger(__name__)


def crear_aplicacion(argv: list[str] | None = None) -> tuple[QApplication, Path]:
    """Configura logging, Qt y el tema; devuelve la aplicación y la ruta del log."""
    log_path = configurar_logging()
    log.info("Preparando la aplicación Qt")

    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv if argv is None else argv)
    app.setApplicationName("Condo Pagos")
    app.setStyle("Fusion")
    app.setStyleSheet(generar_qss())

    return app, log_path
