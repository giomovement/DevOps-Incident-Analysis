from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "DevOps Incident Analysis Suite"
    environment: str = "development"
    database_path: Path = Path("data/incidents.sqlite3")
    checkpoint_path: Path = Path("data/checkpoints.sqlite3")
    storage_path: Path = Path("data/uploads")
    artifact_path: Path = Path("data/artifacts")
    frontend_origin: str = "http://localhost:3000"
    session_cookie_secure: bool = False
    max_incident_bytes: int = 250 * 1024 * 1024
    max_files_per_incident: int = 10
    job_mode: str = "inline"
    redis_url: str = "redis://localhost:6379/0"
    integrations_mode: str = "mock"
    openrouter_api_key: str | None = None
    openrouter_base_url: str | None = None
    openrouter_base_url_chat_completion: str | None = None
    openrouter_extraction_model: str | None = None
    openrouter_reasoning_model: str | None = None
    slack_bot_token: str | None = None
    jira_access_token: str | None = None
    jira_cloud_id: str | None = None
    model_config = SettingsConfigDict(env_file=".env", env_prefix="DIAS_", extra="ignore")

    def ensure_directories(self) -> None:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.artifact_path.mkdir(parents=True, exist_ok=True)


settings = Settings()
