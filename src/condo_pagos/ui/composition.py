# src/condo_pagos/ui/composition.py
from PySide6.QtCore import QThreadPool
from condo_pagos.ui.ports import UiContainer
from condo_pagos.ui.services.navegacion import ServicioNavegacion
from condo_pagos.ui.services.real import ServicioDialogosReal, AbridorArchivosReal
from condo_pagos.ui.services.configuracion import ConfiguracionLocal
from condo_pagos.ui.viewmodels.registrar_pago_vm import RegistrarPagoViewModel
from condo_pagos.ui.viewmodels.unidades_vm import UnidadesViewModel
from condo_pagos.ui.viewmodels.pagos_vm import PagosViewModel
from condo_pagos.ui.views.registrar_pago_view import RegistrarPagoView
from condo_pagos.ui.views.unidades_view import UnidadesView
from condo_pagos.ui.views.pagos_view import PagosView
from condo_pagos.ui.views.main_window import MainWindow

def crear_ventana(container: UiContainer, config: ConfiguracionLocal) -> MainWindow:
    nav = ServicioNavegacion()
    dialogos = ServicioDialogosReal()
    abridor = AbridorArchivosReal()

    # Instanciación de ViewModels conectando servicios y casos de uso
    registrar_vm = RegistrarPagoViewModel(
        buscar_unidades_uc=container.buscar_unidades,
        consultar_estado_uc=container.consultar_estado_cuenta,
        registrar_pago_uc=container.registrar_pago,
    )
    
    unidades_vm = UnidadesViewModel(
        listar_unidades_uc=container.listar_unidades,
        consultar_estado_uc=container.consultar_estado_cuenta,
    )
    # Conectar la navegación desde unidades hacia el registro de pago pasando parámetros
    unidades_vm.navegar_a_pago.connect(lambda unidad: nav.ir_a("registrar_pago", unidad))

    pagos_vm = PagosViewModel(
        listar_pagos_uc=container.listar_pagos,
        emitir_pdf_uc=container.emitir_pdf,
        anular_pago_uc=container.anular_pago,
        abridor_archivos=abridor,
    )

    # Refrescar las pantallas que dependen del saldo/historial después de registrar.
    registrar_vm.pago_registrado.connect(lambda _folio: pagos_vm.cargar_pagos())
    registrar_vm.pago_registrado.connect(unidades_vm.cargar_unidades)

    paginas = {
        "registrar_pago": ("Registrar pago", RegistrarPagoView(registrar_vm)),
        "unidades":       ("Unidades",       UnidadesView(unidades_vm)),
        "pagos":          ("Pagos",          PagosView(pagos_vm)),
    }

    vms = (registrar_vm, unidades_vm, pagos_vm)

    # El nombre del condominio se obtiene del container o un valor por defecto
    nombre_condo = getattr(container, "nombre_condominio", "Condominio Principal")
    QThreadPool.globalInstance().waitForDone()

    def esperar_trabajos() -> None:
        QThreadPool.globalInstance().waitForDone()

    return MainWindow(
        nav=nav,
        paginas=paginas,
        nombre_condominio=nombre_condo,
        hay_operaciones_en_curso=lambda: any(vm.ocupado for vm in vms),
        esperar_trabajos=esperar_trabajos,
    )