from sqlalchemy import text
from condo_pagos.infrastructure.database.engine import engine
from condo_pagos.infrastructure.database.unit_of_work import SqlAlchemyUnitOfWork
from condo_pagos.infrastructure.pdf_generator.reportlab_renderer import ReportLabPdfRenderer
from condo_pagos.infrastructure.storage.filesystem_storage import FileSystemStorage
from condo_pagos.use_cases.registrar_pago import RegistrarPagoUseCase
from condo_pagos.use_cases.anular_pago import AnularPagoUseCase
# Importa otros casos de uso según corresponda en tu proyecto

class Container:
    def __init__(self, uow_factory, pdf_renderer, storage):
        self.uow_factory = uow_factory
        self.pdf_renderer = pdf_renderer
        self.storage = storage

    def registrar_pago_use_case(self) -> RegistrarPagoUseCase:
        # Instanciamos el UoW usando la fábrica y se lo inyectamos al caso de uso
        uow = self.uow_factory()
        return RegistrarPagoUseCase(uow=uow)

    def anular_pago_use_case(self) -> AnularPagoUseCase:
        return AnularPagoUseCase(uow=self.uow_factory)


def verificar_schema_info() -> None:
    """Tarea 3.3: Verifica que la base de datos tenga el esquema inicializado correctamente."""
    with engine.connect() as conn:
        # Envolviendo siempre la consulta SQL en text() para SQLAlchemy 2.0
        query = text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'pagos')")
        res = conn.execute(query).scalar()
        if not res:
            raise RuntimeError("El esquema de la base de datos no está inicializado. Ejecute los scripts SQL correspondientes.")

def build_container() -> Container:
    # 1. Verificar esquema antes de levantar el contenedor
    verificar_schema_info()

    # 2. Instanciar adaptadores de infraestructura reales
    uow_factory = SqlAlchemyUnitOfWork
    pdf_renderer = ReportLabPdfRenderer()
    storage = FileSystemStorage()

    return Container(
        uow_factory=uow_factory,
        pdf_renderer=pdf_renderer,
        storage=storage
    )