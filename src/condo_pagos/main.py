"""Punto de entrada y raíz de composición de Condo Pagos."""

import argparse
import logging
import sys

from PySide6.QtCore import QThreadPool
from PySide6.QtWidgets import QApplication, QMessageBox

from condo_pagos.infrastructure.errors import ErrorDeInfraestructura, EsquemaIncompatible
from condo_pagos.ui.app import crear_aplicacion

log = logging.getLogger(__name__)


def _crear_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Módulo de Pagos - Condominios")
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Ejecuta la aplicación en modo demostración con datos en memoria.",
    )
    return parser


def _crear_container(modo_demo: bool):
    """Construye el contenedor elegido desde la raíz de composición."""
    if modo_demo:
        log.info("Cargando contenedor en memoria")
        from condo_pagos.infrastructure.memory_container import InMemoryContainer

        return InMemoryContainer()

    # Los imports diferidos mantienen la composición fuera de la capa UI.
    try:
        from condo_pagos.config import Settings
        from condo_pagos.infrastructure.bootstrap import build_container
    except ImportError as exc:
        raise RuntimeError(
            "El contenedor de PostgreSQL todavía no está implementado. "
            "Ejecuta con --demo o completa el bootstrap de infraestructura."
        ) from exc

    return build_container(Settings())


def main(argv: list[str] | None = None) -> int:
    """Arranca la UI y coordina el contenedor y el ciclo de eventos."""
    args = _crear_parser().parse_args(argv)
    app: QApplication | None = None
    log_path = None

    try:
        app, log_path = crear_aplicacion(
            [sys.argv[0], *(argv if argv is not None else sys.argv[1:])]
        )
        log.info("Iniciando Condo Pagos (modo=%s)", "demo" if args.demo else "real")

        # Imports de UI diferidos para que sus errores queden registrados.
        from condo_pagos.ui.composition import crear_ventana
        from condo_pagos.ui.services.configuracion import ConfiguracionLocal

        try:
            container = _crear_container(args.demo)
        except (ErrorDeInfraestructura, EsquemaIncompatible) as exc:
            log.error("No se pudo preparar la infraestructura: %s", exc)
            QMessageBox.critical(None, "Condo Pagos", str(exc))
            return 2

        config = ConfiguracionLocal()
        log.info("Construyendo ventana principal")
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
        return exit_code

    except Exception:
        log.exception("Error fatal durante el inicio o ejecución de Condo Pagos")
        if app is not None:
            ruta = str(log_path.resolve()) if log_path is not None else "logs/condo-pagos.log"
            QMessageBox.critical(
                None,
                "Error de Condo Pagos",
                "La aplicación encontró un error y no pudo continuar.\n\n"
                f"Se guardó el detalle técnico en:\n{ruta}",
            )
        raise


if __name__ == "__main__":
    raise SystemExit(main())
