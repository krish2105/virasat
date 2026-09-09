from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://virasat:virasat@localhost:5434/virasat"
    virasat_cloud: bool = False
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


settings = Settings()
