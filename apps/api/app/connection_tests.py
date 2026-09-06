from typing import Any

import httpx

from .ai_config import openrouter_config
from .integration_config import slack_config


class IntegrationNotConfiguredError(RuntimeError):
    pass


class IntegrationValidationError(RuntimeError):
    pass


class IntegrationConnectionError(RuntimeError):
    pass


class UnknownIntegrationError(RuntimeError):
    pass


def _request_error(provider: str, exc: Exception) -> IntegrationConnectionError:
    if isinstance(exc, httpx.HTTPStatusError):
        return IntegrationConnectionError(f"{provider} rejected the connection (HTTP {exc.response.status_code})")
    if isinstance(exc, httpx.TimeoutException):
        return IntegrationConnectionError(f"{provider} connection timed out")
    return IntegrationConnectionError(f"{provider} connection failed: {type(exc).__name__}")


def test_openrouter_connection(workspace_id: str) -> dict[str, Any]:
    config = openrouter_config(workspace_id)
    if not config.api_key:
        raise IntegrationNotConfiguredError("Add and save an OpenRouter API key before testing")
    if not config.model:
        raise IntegrationNotConfiguredError("Add and save an OpenRouter model before testing")

    api_root = config.endpoint.rsplit("/chat/completions", 1)[0]
    key_endpoint = api_root + "/key"
    models_endpoint = api_root + "/models"
    try:
        key_response = httpx.get(key_endpoint, headers={"Authorization": f"Bearer {config.api_key}"}, timeout=20)
        key_response.raise_for_status()
        key_payload = key_response.json()
        if not isinstance(key_payload, dict) or not isinstance(key_payload.get("data"), dict):
            raise IntegrationConnectionError("OpenRouter returned an unexpected key response")

        response = httpx.get(models_endpoint, headers={"Authorization": f"Bearer {config.api_key}"}, timeout=20)
        response.raise_for_status()
        payload = response.json()
    except IntegrationConnectionError:
        raise
    except Exception as exc:
        raise _request_error("OpenRouter", exc) from exc

    models = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(models, list):
        raise IntegrationConnectionError("OpenRouter returned an unexpected response")
    if not any(isinstance(item, dict) and item.get("id") == config.model for item in models):
        raise IntegrationValidationError(f"Connected, but model '{config.model}' was not found")
    return {"provider": "openrouter", "status": "connected", "model": config.model}


def test_slack_connection(workspace_id: str) -> dict[str, Any]:
    config = slack_config(workspace_id)
    if not config.bot_token:
        raise IntegrationNotConfiguredError("Add and save a Slack bot token before testing")
    if not config.channel_id:
        raise IntegrationNotConfiguredError("Add and save a Slack channel ID before testing")

    headers = {"Authorization": f"Bearer {config.bot_token}"}
    try:
        auth_response = httpx.post("https://slack.com/api/auth.test", headers=headers, timeout=20)
        auth_response.raise_for_status()
        auth = auth_response.json()
        if not auth.get("ok"):
            raise IntegrationConnectionError(f"Slack authentication failed: {auth.get('error', 'unknown error')}")

        channel_response = httpx.get(
            "https://slack.com/api/conversations.info",
            headers=headers,
            params={"channel": config.channel_id},
            timeout=20,
        )
        channel_response.raise_for_status()
        channel = channel_response.json()
        channel_error = channel.get("error")
        if not channel.get("ok"):
            if channel_error == "missing_scope":
                raise IntegrationValidationError(
                    "Slack token is valid, but channel verification requires channels:read for public channels or groups:read for private channels"
                )
            if channel_error == "channel_not_found":
                raise IntegrationValidationError("Slack channel was not found or is not accessible to this bot")
            raise IntegrationConnectionError(f"Slack channel check failed: {channel_error or 'unknown error'}")
    except (IntegrationConnectionError, IntegrationValidationError):
        raise
    except Exception as exc:
        raise _request_error("Slack", exc) from exc

    channel_name = channel.get("channel", {}).get("name")
    return {
        "provider": "slack",
        "status": "connected",
        "workspace": auth.get("team"),
        "channel": channel_name or config.channel_id,
        "channel_verified": True,
    }


def test_provider_connection(provider: str, workspace_id: str) -> dict[str, Any]:
    if provider == "openrouter":
        return test_openrouter_connection(workspace_id)
    if provider == "slack":
        return test_slack_connection(workspace_id)
    if provider == "jira":
        raise IntegrationNotConfiguredError("Jira connection testing is not available")
    raise UnknownIntegrationError("Unknown integration")
