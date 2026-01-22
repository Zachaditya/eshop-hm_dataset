# app/core/config.py
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",          # local only; Railway env vars still work fine
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = Field(..., alias="DATABASE_URL")
    image_base_url: str | None = Field(default=None, alias="IMAGE_BASE_URL")


    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, v: str) -> str:
        url = str(v).strip()

        # normalize legacy scheme
        url = url.replace("postgres://", "postgresql://")

        # force psycopg v3 driver so SQLAlchemy doesn't look for psycopg2
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+psycopg://", 1)

        return url


settings = Settings()
