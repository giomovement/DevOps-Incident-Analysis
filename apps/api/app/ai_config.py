import json
from dataclasses import dataclass

from .config import settings
from .database import db


@dataclass(frozen=True)
class OpenRouterConfig:
    api_key: str | None
    model: str | None
    endpoint: str

    @property
    def configured(self) -> bool:
        return bool(self.api_key and self.model and self.endpoint)


def openrouter_config(workspace_id: str | None = None) -> OpenRouterConfig:
    """Resolve workspace settings first, then fall back to server environment values."""
    if workspace_id:
        with db() as conn:
            row = conn.execute(
                "SELECT secret_ref,metadata FROM integrations WHERE workspace_id=? AND provider='openrouter'",
                (workspace_id,),
            ).fetchone()
        if row:
            metadata = json.loads(row["metadata"] or "{}")
            return OpenRouterConfig(
                api_key=row["secret_ref"] or None,
                model=metadata.get("model") or None,
                endpoint=settings.openrouter_base_url_chat_completion or "https://openrouter.ai/api/v1/chat/completions",
            )
    return OpenRouterConfig(
        api_key=settings.openrouter_api_key,
        model=settings.openrouter_reasoning_model,
        endpoint=settings.openrouter_base_url_chat_completion or "https://openrouter.ai/api/v1/chat/completions",
    )
