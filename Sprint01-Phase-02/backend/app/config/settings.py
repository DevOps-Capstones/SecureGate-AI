from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "SecureGate AI"
    app_version: str = "0.1.0"
    database_url: str = "postgresql://securegate:securegate_password@localhost:5432/securegate"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
