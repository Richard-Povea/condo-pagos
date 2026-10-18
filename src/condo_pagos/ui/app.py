"""Punto de entrada de la interfaz gráfica."""

import argparse
import logging
import sys

from PySide6.QtCore import QThreadPool, Qt
from PySide6.QtWidgets import QApplication, QMessageBox

from condo_pagos.ui.logging_config import configurar_logging

log = logging.getLogger(__name__)


def main() -> None:
    log_path = configurar_logging()
    parser = argparse.ArgumentParser(description="Módulo de Pagos - Condominios")
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Ejecuta la aplicación en modo demostración con datos en memoria.",
    )
    args = parser.parse_args()

    app = None
    try:
        log.info("Iniciando Condo Pagos (modo=%s)", "demo" if args.demo else "real")
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )

        app = QApplication(sys.argv)
        app.setApplicationName("Condo Pagos")
        app.setStyle("Fusion")

        # Imports diferidos para que sus errores también queden registrados.
        from condo_pagos.ui.composition import crear_ventana
        from condo_pagos.ui.services.configuracion import ConfiguracionLocal
        from condo_pagos.ui.theme.theme import generar_qss

        app.setStyleSheet(generar_qss())

        if args.demo:
            log.info("Cargando contenedor en memoria")
            from condo_pagos.infrastructure.memory_container import InMemoryContainer

            container = InMemoryContainer()
        else:
            log.info("Cargando contenedor de PostgreSQL")
            from condo_pagos.infrastructure.container import Settings, build_container

            container = build_container(Settings())

        log.info("Construyendo ventana principal")
        config = ConfiguracionLocal()
        window = crear_ventana(container, config)
        window.show()
        log.info("Ventana principal mostrada; iniciando ciclo de eventos")

        exit_code = app.exec()
        log.info("Ciclo de eventos finalizado con código %s", exit_code)

        pool = QThreadPool.globalInstance()
        if pool.activeThreadCount() > 0:
            log.info("Esperando tareas asíncronas pendientes")
            pool.waitForDone(3000)

        log.info("Cierre de Condo Pagos")
        raise SystemExit(exit_code)

    except SystemExit:
        raise
    except Exception:
        log.exception("Error fatal durante el inicio o ejecución de Condo Pagos")
        if app is not None:
            QMessageBox.critical(
                None,
                "Error de Condo Pagos",
                "La aplicación encontró un error y no pudo continuar.\n\n"
                f"Se guardó el detalle técnico en:\n{log_path.resolve()}",
            )
        raise


if __name__ == "__main__":
    main()
