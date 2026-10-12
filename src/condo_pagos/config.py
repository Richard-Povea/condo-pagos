from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

CONDO_DATABASE_URL="postgresql+psycopg://condo_app:condo_dev_pw@localhost:5432/condo_dev"

class Settings(BaseSettings):
    condo_database_url: str = (CONDO_DATABASE_URL)
    pdf_dir: Path = Path("./storage/pdfs")

    model_config = SettingsConfigDict(
        env_file=".env", env_prefix="CONDO_", extra="ignore"
    )


settings = Settings()