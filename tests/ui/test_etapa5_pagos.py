import pytest

from condo_pagos.ui.viewmodels.pagos_vm import PagosViewModel


@pytest.mark.unit
def test_anular_pago_motivo_invalido():
    vm = PagosViewModel(
        listar_pagos_uc=lambda **kwargs: None,
        emitir_pdf_uc=lambda uid: "",
        anular_pago_uc=lambda **kwargs: "FOLIO-01",
        abridor_archivos=lambda ruta: None
    )

    # Motivo con menos de 10 caracteres debe lanzar ValueError
    with pytest.raises(ValueError, match="al menos 10 caracteres"):
        vm.anular_pago("id_pago", motivo="Corto", operador="Cajero")

class ResultadoPaginadoMock:
    def __init__(self, filas, total_paginas):
        self.filas = filas
        self.total_paginas = total_paginas

@pytest.mark.unit
def test_anular_pago_motivo_valido(qtbot):
    anulado_ok = []
    vm = PagosViewModel(
        listar_pagos_uc=lambda **kwargs: ResultadoPaginadoMock([], 1),
        emitir_pdf_uc=lambda uid: "",
        anular_pago_uc=lambda **kwargs: "FOLIO-01",
        abridor_archivos=lambda ruta: None
    )
    vm.pago_anulado.connect(lambda folio: anulado_ok.append(folio))

    vm.anular_pago(
        "id_pago",
        motivo="Este motivo de anulación es suficientemente largo y válido.",
        operador="Cajero"
    )
    
    # Esperamos de forma síncrona a que el hilo secundario y los eventos terminen
    qtbot.waitUntil(lambda: len(anulado_ok) > 0, timeout=1000)

    assert "FOLIO-01" in anulado_ok