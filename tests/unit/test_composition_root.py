"""Guardas estructurales para mantener una sola raíz de composición."""

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_hay_una_sola_raiz_de_composicion() -> None:
    raices = [
        path.relative_to(ROOT).as_posix()
        for path in (ROOT / "src").rglob("*.py")
        if "def build_container" in path.read_text(encoding="utf-8")
    ]
    assert raices == ["src/condo_pagos/bootstrap.py"], raices


def test_bootstrap_solo_se_importa_desde_main_en_src() -> None:
    infracciones: list[str] = []
    for path in (ROOT / "src").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        importa_bootstrap = any(
            (isinstance(node, ast.ImportFrom) and node.module == "condo_pagos.bootstrap")
            or (
                isinstance(node, ast.Import)
                and any(alias.name == "condo_pagos.bootstrap" for alias in node.names)
            )
            for node in ast.walk(tree)
        )
        if importa_bootstrap and path.relative_to(ROOT).as_posix() != "src/condo_pagos/main.py":
            infracciones.append(path.relative_to(ROOT).as_posix())
    assert not infracciones, infracciones

def test_las_pruebas_solo_construyen_el_contenedor_desde_el_fixture_comun() -> None:
    infracciones: list[str] = []
    for path in (ROOT / "tests").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        construye_contenedor = any(
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "build_container"
            for node in ast.walk(tree)
        )
        if (
            construye_contenedor
            and path.relative_to(ROOT).as_posix() != "tests/conftest.py"
        ):
            infracciones.append(path.relative_to(ROOT).as_posix())
    assert not infracciones, infracciones
