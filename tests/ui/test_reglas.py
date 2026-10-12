import importlib
import pkgutil
import pytest
from condo_pagos.ui import viewmodels

@pytest.mark.unit
def test_viewmodels_sin_widgets():
    """Recorre todos los módulos en ui/viewmodels y falla si importan QtWidgets."""
    package = viewmodels
    for _, modname, _ in pkgutil.walk_packages(package.__path__, package.__name__ + "."):
        module = importlib.import_module(modname)
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            # Verificamos que sea una clase, función o tipo con __module__
            if isinstance(attr, (type, type(lambda: None))) and hasattr(attr, "__module__") and attr.__module__:
                if "PySide6.QtWidgets" in attr.__module__:
                    pytest.fail(f"El ViewModel {modname} importa elementos prohibidos de QtWidgets ({attr_name}).")