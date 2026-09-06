import json
from dataclasses import dataclass

from .config import settings
from .database import db


@dataclass(frozen=True)
class SlackConfig:
    bot_token: str | None
    channel_id: str
    workspace_override: bool = False

    @property
    def configured(self) -> bool:
        return bool(self.bot_token and self.channel_id)


def slack_config(workspace_id: str | None = None) -> SlackConfig:
    if workspace_id:
        with db() as conn:
            row = conn.execute(
                "SELECT secret_ref,metadata FROM integrations WHERE workspace_id=? AND provider='slack'",
                (workspace_id,),
            ).fetchone()
        if row:
            metadata = json.loads(row["metadata"] or "{}")
            return SlackConfig(row["secret_ref"] or None, metadata.get("channel_id") or "", True)
    return SlackConfig(settings.slack_bot_token, settings.slack_default_channel)
