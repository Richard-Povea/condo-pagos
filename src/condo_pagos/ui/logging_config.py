"""Configuración centralizada de logs para diagnóstico de la aplicación."""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import sys


def configurar_logging() -> Path:
    """Configura consola y archivo rotativo; devuelve la ruta del archivo."""
    log_dir = Path.cwd() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "condo-pagos.log"

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    # Evita duplicar handlers si la aplicación se inicializa más de una vez.
    if not any(getattr(handler, "_condo_pagos_handler", False) for handler in root.handlers):
        formato = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(filename)s:%(lineno)d | %(message)s"
        )

        archivo = RotatingFileHandler(
            log_path,
            maxBytes=2_000_000,
            backupCount=3,
            encoding="utf-8",
        )
        archivo.setLevel(logging.DEBUG)
        archivo.setFormatter(formato)
        archivo._condo_pagos_handler = True  # type: ignore[attr-defined]
        root.addHandler(archivo)

        consola = logging.StreamHandler()
        consola.setLevel(logging.INFO)
        consola.setFormatter(formato)
        consola._condo_pagos_handler = True  # type: ignore[attr-defined]
        root.addHandler(consola)

    def manejar_excepcion(tipo, valor, traceback) -> None:
        if issubclass(tipo, KeyboardInterrupt):
            sys.__excepthook__(tipo, valor, traceback)
            return
        logging.getLogger("condo_pagos.excepciones").critical(
            "Excepción no capturada", exc_info=(tipo, valor, traceback)
        )

    sys.excepthook = manejar_excepcion
    logging.getLogger(__name__).info("Logging iniciado. Archivo: %s", log_path.resolve())
    return log_path
