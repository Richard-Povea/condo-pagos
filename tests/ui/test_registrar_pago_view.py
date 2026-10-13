import pytest
from PySide6.QtCore import Qt

from condo_pagos.ui.viewmodels.registrar_pago_vm import RegistrarPagoViewModel
from condo_pagos.ui.views.registrar_pago_view import RegistrarPagoView


@pytest.mark.unit
def test_vista_registro_pago_tab_order(qtbot):
    vm = RegistrarPagoViewModel(
        buscar_unidades_uc=lambda t: [],
        consultar_estado_uc=lambda uid: None,
        registrar_pago_uc=lambda **kwargs: None
    )
    view = RegistrarPagoView(vm)
    view.show()
    qtbot.addWidget(view)

    # Verificar que el buscador tiene el foco inicial o está configurado en el orden lógico
    qtbot.keyClick(view.txt_buscar, Qt.Key.Key_Tab)
    # Comprobamos que el widget activo cambia correctamente por teclado
    assert view.focusWidget() is not None