import argparse
import logging
import sys

from PySide6.QtCore import QThreadPool, Qt
from PySide6.QtWidgets import QApplication

from condo_pagos.ui.composition import crear_ventana
from condo_pagos.ui.services.configuracion import ConfiguracionLocal
from condo_pagos.ui.theme.theme import generar_qss

log = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="Módulo de Pagos - Condominios")
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Ejecuta la aplicación en modo demostración con datos en memoria.",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(generar_qss())

    # Los contenedores se importan de forma diferida para mantener el arranque
    # de la UI desacoplado de la infraestructura hasta seleccionar el modo.
    if args.demo:
        from condo_pagos.infrastructure.memory_container import InMemoryContainer

        container = InMemoryContainer()
    else:
        from condo_pagos.infrastructure.container import Settings, build_container

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
