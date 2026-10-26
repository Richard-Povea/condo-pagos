"""Fábricas explícitas para conexiones y sesiones SQLAlchemy.

Este módulo no crea conexiones al importarse. La raíz de composición decide
qué URL usar y entrega el engine o la fábrica de sesiones a sus consumidores.
"""

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker


def crear_engine(
    url: str,
    *,
    pool_size: int = 5,
    max_overflow: int = 5,
    search_path: str = "gc,public",
) -> Engine:
    """Crea un engine para la URL recibida, sin estado global de módulo."""
    return create_engine(
        url,
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_pre_ping=True,
        connect_args={
            "connect_timeout": 5,
            "options": f"-c search_path={search_path}",
        },
    )


def crear_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Crea una fábrica de sesiones ligada al engine explícitamente recibido."""
    return sessionmaker(bind=engine, expire_on_commit=False)
