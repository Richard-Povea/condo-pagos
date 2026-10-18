# src/condo_pagos/ui/app.py
import sys
import argparse
import logging
from PySide6.QtCore import Qt, QThreadPool
from PySide6.QtWidgets import QApplication, QMessageBox
from condo_pagos.ui.composition import crear_ventana
from condo_pagos.ui.services.configuracion import ConfiguracionLocal
from condo_pagos.ui.theme.theme import generar_qss

# Contenedores (ejemplo condicional entre demo y real)
# from condo_pagos.infra.container import build_container, Settings
# from condo_pagos.infra.memory_container import InMemoryContainer

log = logging.getLogger(__name__)

def main() -> None:
    parser = argparse.ArgumentParser(description="Módulo de Pagos - Condominios")
    parser.add_argument("--demo", action="store_true", help="Ejecuta la aplicación en modo demostración con datos en memoria.")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(generar_qss())

    # Selección de contenedor según el argumento --demo
    if args.demo:
        # Contenedor en memoria (InMemoryContainer)
        from condo_pagos.infra.memory_container import InMemoryContainer  # Ajustar según la ruta exacta del proyecto
        container = InMemoryContainer()
    else:
        # Contenedor real con Postgres
        from condo_pagos.infra.container import build_container, Settings  # Ajustar según la ruta exacta del proyecto
        container = build_container(Settings())

    config = ConfiguracionLocal()
    window = crear_ventana(container, config)
    window.show()

    exit_code = app.exec()

    pool = QThreadPool.globalInstance()
    if pool.activeThreadCount() > 0:
        log.info("Esperando tareas asíncronas pendientes...")
        pool.waitForDone(3000)

    sys.exit(exit_code)

if __name__ == "__main__":
    main()