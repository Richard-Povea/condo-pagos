import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://condo_app:condo_dev_pw@localhost:5432/condo_dev"
)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    future=True,
    # Configurar el search_path para que el esquema 'gc' sea el principal
    connect_args={"options": "-c search_path=gc,public"}
)

SessionLocal = sessionmaker(
    bind=engine,
    expire_on_commit=False,
    future=True,
)