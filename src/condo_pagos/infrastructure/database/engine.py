import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool  # <-- Importar NullPool

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://condo_test:condo_test_pw@localhost:5433/condo_test"
)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    future=True,
    connect_args={"options": "-c search_path=gc,public"},
    poolclass=NullPool,  # <-- Crucial para pruebas de concurrencia con hilos
)

SessionLocal = sessionmaker(
    bind=engine,
    expire_on_commit=False,
    future=True,
)