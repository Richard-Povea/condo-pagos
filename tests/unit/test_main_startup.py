"""Pruebas de humo del arranque real/demo y del cierre del contenedor."""

from typing import Any

import condo_pagos.main as main_module


class _FakeApp:
    def exec(self) -> int:
        return 0


class _FakeContainer:
    nombre_condominio = "Condominio de prueba"

    def __init__(self) -> None:
        self.cerrado = False

    def cerrar(self) -> None:
        self.cerrado = True


class _FakeWindow:
    def __init__(self) -> None:
        self.mostrada = False

    def show(self) -> None:
        self.mostrada = True


def _preparar_ui(monkeypatch: Any) -> tuple[_FakeApp, _FakeWindow]:
    app = _FakeApp()
    window = _FakeWindow()
    monkeypatch.setattr(main_module, "crear_aplicacion", lambda _args: (app, None))

    import condo_pagos.ui.composition as composition
    import condo_pagos.ui.services.configuracion as configuracion

    monkeypatch.setattr(composition, "crear_ventana", lambda _container, _config: window)
    monkeypatch.setattr(configuracion, "ConfiguracionLocal", lambda: object())
    return app, window


def test_arranque_demo_muestra_ventana_y_cierra_contenedor(monkeypatch: Any) -> None:
    container = _FakeContainer()
    _preparar_ui(monkeypatch)

    import condo_pagos.infrastructure.memory_container as memory_container

    monkeypatch.setattr(memory_container, "InMemoryContainer", lambda: container)

    assert main_module.main(["--demo"]) == 0
    assert container.cerrado


def test_arranque_real_muestra_ventana_y_cierra_contenedor(monkeypatch: Any) -> None:
    container = _FakeContainer()
    _preparar_ui(monkeypatch)

    import condo_pagos.config as config
    import condo_pagos.infrastructure.bootstrap as bootstrap

    monkeypatch.setattr(config, "Settings", lambda: object())
    monkeypatch.setattr(bootstrap, "build_container", lambda _settings: container)

    assert main_module.main([]) == 0
    assert container.cerrado
