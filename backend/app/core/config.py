"""Application settings loaded from environment variables and local .env files."""

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed backend configuration shared by API routes and services."""

    model_config = SettingsConfigDict(
        env_file=".env",          # local only; Railway env vars still work fine
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = Field(..., alias="DATABASE_URL")
    image_base_url: str | None = Field(default=None, alias="IMAGE_BASE_URL")
    agent_api_key: str | None = Field(default=None, alias="AGENT_API_KEY")
    merchant_pay_to_address: str = Field(
        default="0xa7BD909D765d9e93f75a0d76E77827a6EdC8A69D",
        alias="MERCHANT_PAY_TO_ADDRESS",
    )
    base_sepolia_rpc_url: str = Field(
        default="https://sepolia.base.org",
        alias="BASE_SEPOLIA_RPC_URL",
    )
    usdc_contract_address: str = Field(
        default="0x036CbD53842c5426634e7929541eC2318f3dCF7e",
        alias="USDC_CONTRACT_ADDRESS",
    )
    agent_demo_user_email: str | None = Field(default=None, alias="AGENT_DEMO_USER_EMAIL")


    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, v: str) -> str:
        """
        Normalize database URLs before SQLAlchemy creates an engine.

        Params:
            v: Raw database URL from the environment or settings source.

        Returns:
            A stripped SQLAlchemy URL with legacy postgres schemes converted to
            the psycopg v3 dialect used by this backend.
        """
        url = str(v).strip()

        # normalize legacy scheme
        url = url.replace("postgres://", "postgresql://")

        # force psycopg v3 driver so SQLAlchemy doesn't look for psycopg2
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+psycopg://", 1)

        return url

    @field_validator(
        "agent_api_key",
        "merchant_pay_to_address",
        "base_sepolia_rpc_url",
        "usdc_contract_address",
        "agent_demo_user_email",
        mode="before",
    )
    @classmethod
    def strip_optional_strings(cls, v: str | None) -> str | None:
        """
        Trim whitespace from optional string settings while preserving blanks.

        Params:
            v: Raw optional setting value from the environment or .env file.

        Returns:
            The stripped value, or None when the source value is absent.
        """
        if v is None:
            return None
        return str(v).strip()


settings = Settings()
