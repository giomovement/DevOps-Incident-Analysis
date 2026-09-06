import os
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def default_storage_path() -> Path:
    return Path("/tmp/dias/uploads") if os.getenv("VERCEL") else Path("data/uploads")


def default_secure_cookie() -> bool:
    return bool(os.getenv("VERCEL"))


class Settings(BaseSettings):
    app_name: str = "DevOps Incident Analysis Suite"
    environment: str = "development"
    database_url: str | None = None
    database_path: Path = Path("data/incidents.sqlite3")
    storage_path: Path = Field(default_factory=default_storage_path)
    frontend_origin: str = "http://localhost:3000"
    session_cookie_secure: bool = Field(default_factory=default_secure_cookie)
    max_incident_bytes: int = 3 * 1024 * 1024
    max_files_per_incident: int = 5
    integrations_mode: str = "mock"
    openrouter_api_key: str | None = None
    openrouter_base_url: str | None = None
    openrouter_base_url_chat_completion: str | None = None
    openrouter_extraction_model: str | None = None
    openrouter_reasoning_model: str | None = None
    slack_bot_token: str | None = None
    # Use a channel ID (for example C0123456789), rather than a display name.
    # IDs remain stable if a Slack channel is renamed.
    slack_default_channel: str = "#incidents"
    slack_default_channel_name: str | None = None
    jira_access_token: str | None = None
    jira_cloud_id: str | None = None
    model_config = SettingsConfigDict(env_file=".env", env_prefix="DIAS_", extra="ignore")

    def ensure_directories(self) -> None:
        if os.getenv("VERCEL") and not self.database_url:
            raise RuntimeError("DIAS_DATABASE_URL is required on Vercel")
        if not self.database_url:
            self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.storage_path.mkdir(parents=True, exist_ok=True)


settings = Settings()
