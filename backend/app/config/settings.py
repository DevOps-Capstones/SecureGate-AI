from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "SecureGate AI"
    app_version: str = "0.4.0"
    database_url: str = "postgresql://securegate:securegate_password@localhost:5432/securegate"
    securegate_api_key: str = "change-me"
    storage_root: str = "storage"
    public_backend_url: str = "http://localhost:8000"
    github_trigger_token: str | None = None
    github_workflow_file: str = "securegate.yml"
    slack_webhook_url: str | None = None
    slack_channel_name: str | None = "#securegate-alerts"
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from: str | None = None
    prometheus_enabled: bool = True
    alertmanager_url: str = "http://alertmanager:9093"
    alert_escalation_minutes: int = 30
    security_score_threshold: int = 80
    critical_vulnerability_threshold: int = 0
    high_vulnerability_threshold: int = 5
    block_high_vulnerabilities: bool = True
    quality_gate_required: bool = True
    secret_detection_required: bool = True
    enable_monitoring: bool = True
    enable_analytics: bool = True
    ai_enabled: bool = True
    ollama_base_url: str = "http://ollama:11434"
    ollama_model: str = "gemma3:4b"
    ollama_timeout_seconds: int = 15
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
