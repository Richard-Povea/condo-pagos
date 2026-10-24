from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    condo_database_url: str = Field(
        default="postgresql+psycopg://condo_app:condo_dev_pw@localhost:5432/condo_dev",
        validation_alias="CONDO_DATABASE_URL",
    )
    pdf_dir: Path = Path("./storage/pdfs")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="CONDO_",
        populate_by_name=True,
        extra="ignore",
    )


settings = Settings()
