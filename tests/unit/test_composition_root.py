"""Guardas estructurales para mantener una sola raíz de composición."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_hay_una_sola_raiz_de_composicion() -> None:
    raices = [
        path.relative_to(ROOT).as_posix()
        for path in (ROOT / "src").rglob("*.py")
        if "def build_container" in path.read_text(encoding="utf-8")
    ]
    assert raices == ["src/condo_pagos/bootstrap.py"], raices
