"""Punto de composición legado para los casos de uso de pagos."""

from collections.abc import Callable

from sqlalchemy import Engine, text

from condo_pagos.config import Settings
from condo_pagos.infrastructure.database.engine import crear_engine, crear_session_factory
from condo_pagos.infrastructure.database.unit_of_work import SqlAlchemyUnitOfWork
from condo_pagos.infrastructure.pdf_generator.reportlab_renderer import ReportLabPdfRenderer
from condo_pagos.infrastructure.storage.filesystem_storage import FileSystemStorage
from condo_pagos.use_cases.anular_pago import AnularPagoUseCase
from condo_pagos.use_cases.registrar_pago import RegistrarPagoUseCase


class Container:
    """Contenedor legado con dependencias explícitas y cierre de recursos."""

    def __init__(
        self,
        engine: Engine,
        uow_factory: Callable[[], SqlAlchemyUnitOfWork],
        pdf_renderer: ReportLabPdfRenderer,
        storage: FileSystemStorage,
    ) -> None:
        self.engine = engine
        self.uow_factory = uow_factory
        self.pdf_renderer = pdf_renderer
        self.storage = storage

    def registrar_pago_use_case(self) -> RegistrarPagoUseCase:
        return RegistrarPagoUseCase(uow=self.uow_factory())

    def anular_pago_use_case(self) -> AnularPagoUseCase:
        return AnularPagoUseCase(uow=self.uow_factory())

    def cerrar(self) -> None:
        """Libera las conexiones creadas por este contenedor."""
        self.engine.dispose()


def verificar_schema_info(engine: Engine) -> None:
    """Verifica que la base de datos tenga la tabla de pagos inicializada."""
    with engine.connect() as conn:
        query = text(
            "SELECT EXISTS ("
            "SELECT FROM information_schema.tables "
            "WHERE table_schema = 'gc' AND table_name = 'pagos'"
            ")"
        )
        existe = conn.execute(query).scalar_one()
        if not existe:
            raise RuntimeError(
                "El esquema de la base de datos no está inicializado. "
                "Ejecute los scripts SQL correspondientes."
            )


def build_container(settings: Settings | None = None) -> Container:
    """Construye el contenedor y sus dependencias a partir de configuración explícita."""
    configuracion = settings or Settings()
    engine = crear_engine(configuracion.condo_database_url)
    try:
        verificar_schema_info(engine)
        session_factory = crear_session_factory(engine)
        uow_factory = lambda: SqlAlchemyUnitOfWork(session_factory)
        return Container(
            engine=engine,
            uow_factory=uow_factory,
            pdf_renderer=ReportLabPdfRenderer(),
            storage=FileSystemStorage(),
        )
    except Exception:
        engine.dispose()
        raise
