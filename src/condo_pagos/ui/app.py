# src/condo_pagos/ui/app.py (Actualización de soporte global)
import sys
import logging
from PySide6.QtCore import Qt, QThreadPool
from PySide6.QtWidgets import QApplication, QMessageBox
from condo_pagos.ui.main_window import MainWindow
from condo_pagos.ui.theme.theme import generar_qss

log = logging.getLogger(__name__)

def _excepthook(exc_type, exc_value, exc_tb):
    log.exception("Excepción no controlada capturada globalmente", exc_info=(exc_type, exc_value, exc_tb))
    QMessageBox.critical(
        None,
        "Error Inesperado",
        "Ocurrió un problema inesperado. El detalle quedó registrado en el sistema."
    )

def main() -> None:
    sys.excepthook = _excepthook
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(generar_qss())

    window = MainWindow()
    window.show()

    exit_code = app.exec()

    # Cierre ordenado del pool de hilos
    pool = QThreadPool.globalInstance()
    if pool.activeThreadCount() > 0:
        log.info("Esperando la finalización de tareas asíncronas pendientes...")
        pool.waitForDone(3000)

    sys.exit(exit_code)

if __name__ == "__main__":
    main()