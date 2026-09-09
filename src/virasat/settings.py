from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://virasat:virasat@localhost:5434/virasat"
    virasat_cloud: bool = False
    # The hosted API carries no model runtime by design: the agent graph runs on the
    # owner's machine (ARCHITECTURE amendment 9). Set this there so /health reports the
    # absence of Ollama as the intended shape, not as a fault.
    virasat_api_only: bool = False
    anthropic_api_key: str = ""
    ollama_base_url: str = "http://localhost:11434"
    mapillary_token: str = ""
    jwt_secret: str = "change-me"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    cors_origins: str = "http://localhost:3000"
    cookie_secure: bool = False

    @field_validator("database_url")
    @classmethod
    def _psycopg_driver(cls, v: str) -> str:
        """Managed hosts hand out a driverless URL; SQLAlchemy would then reach for
        psycopg2, which is not installed."""
        for prefix in ("postgresql://", "postgres://"):
            if v.startswith(prefix):
                return "postgresql+psycopg://" + v[len(prefix) :]
        return v


settings = Settings()
