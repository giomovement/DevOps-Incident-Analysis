from http.client import HTTPException
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from collections.abc import AsyncIterator
from typing import Any
from uuid import uuid4

import httpx

from .config import settings


class LLMProvider(ABC):
    @abstractmethod
    async def structured_generate(self, *, model: str, messages: list[dict], schema: dict) -> dict: ...
    @abstractmethod
    async def chat(self, *, model: str, messages: list[dict]) -> str: ...
    @abstractmethod
    async def stream_chat(self, *, model: str, messages: list[dict]) -> AsyncIterator[str]: ...


class OpenRouterProvider(LLMProvider):
    if not settings.openrouter_base_url_chat_completion:
        raise HTTPException(503, "DIAS_OPENROUTER_BASE_URL_CHAT_COMPLETION is not configured")

    endpoint = settings.openrouter_base_url_chat_completion

    async def structured_generate(self, *, model: str, messages: list[dict], schema: dict) -> dict:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(self.endpoint, headers={"Authorization": f"Bearer {settings.openrouter_api_key}"}, json={"model": model, "messages": messages, "response_format": {"type": "json_schema", "json_schema": {"name": "incident_output", "strict": True, "schema": schema}}, "provider": {"require_parameters": True}})
            response.raise_for_status()
            return json.loads(response.json()["choices"][0]["message"]["content"])

    async def chat(self, *, model: str, messages: list[dict]) -> str:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(self.endpoint, headers={"Authorization": f"Bearer {settings.openrouter_api_key}"}, json={"model": model, "messages": messages})
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]

    async def stream_chat(self, *, model: str, messages: list[dict]) -> AsyncIterator[str]:
        async with httpx.AsyncClient(timeout=60) as client:
            async with client.stream("POST", self.endpoint, headers={"Authorization": f"Bearer {settings.openrouter_api_key}"}, json={"model": model, "messages": messages, "stream": True}) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    payload = line[6:]
                    if payload == "[DONE]":
                        break
                    content = json.loads(payload).get("choices", [{}])[0].get("delta", {}).get("content")
                    if content:
                        yield content


class MockLLMProvider(LLMProvider):
    async def structured_generate(self, *, model: str, messages: list[dict], schema: dict) -> dict:
        return {"summary": "Mock structured response", "model": model}

    async def chat(self, *, model: str, messages: list[dict]) -> str:
        return "The available evidence points to the highest-confidence finding. No remediation has been executed."

    async def stream_chat(self, *, model: str, messages: list[dict]) -> AsyncIterator[str]:
        for token in ("The available evidence points to the highest-confidence finding. ", "No remediation has been executed."):
            yield token


def llm_provider() -> LLMProvider:
    if settings.openrouter_api_key and settings.openrouter_reasoning_model:
        return OpenRouterProvider()
    return MockLLMProvider()


class DeliveryAdapter(ABC):
    @abstractmethod
    def test(self) -> dict: ...
    @abstractmethod
    def deliver(self, *, destination: str, payload: dict, idempotency_key: str) -> dict: ...


@dataclass
class MockDeliveryAdapter(DeliveryAdapter):
    provider: str
    def test(self) -> dict:
        return {"provider": self.provider, "status": "connected", "mode": "mock"}
    def deliver(self, *, destination: str, payload: dict, idempotency_key: str) -> dict:
        suffix = idempotency_key[-8:]
        if self.provider == "jira":
            return {"external_id": f"OPS-{int(suffix, 16) % 9000 + 1000}", "external_url": f"https://jira.example.test/browse/OPS-{int(suffix, 16) % 9000 + 1000}"}
        return {"external_id": f"mock-message-{suffix}", "external_url": None}


@dataclass
class SlackOfficialAdapter(DeliveryAdapter):
    token: str
    def test(self) -> dict:
        response = httpx.post("https://slack.com/api/auth.test", headers={"Authorization": f"Bearer {self.token}"}, timeout=20)
        response.raise_for_status(); data = response.json()
        if not data.get("ok"): raise RuntimeError(data.get("error", "Slack authentication failed"))
        return {"provider": "slack", "status": "connected", "mode": "official", "workspace": data.get("team")}
    def deliver(self, *, destination: str, payload: dict, idempotency_key: str) -> dict:
        if not payload.get("text"):
            raise ValueError("Slack message text is required")
        response = httpx.post("https://slack.com/api/chat.postMessage", headers={"Authorization": f"Bearer {self.token}"}, json={"channel": destination, "text": payload["text"], "client_msg_id": idempotency_key}, timeout=30)
        response.raise_for_status(); data = response.json()
        if not data.get("ok"): raise RuntimeError(data.get("error", "Slack delivery failed"))
        return {"external_id": data["ts"], "external_url": None}


@dataclass
class JiraOfficialAdapter(DeliveryAdapter):
    token: str
    cloud_id: str
    @property
    def base(self): return f"https://api.atlassian.com/ex/jira/{self.cloud_id}"
    def test(self) -> dict:
        response = httpx.get(f"{self.base}/rest/api/3/myself", headers={"Authorization": f"Bearer {self.token}", "Accept": "application/json"}, timeout=20)
        response.raise_for_status(); data = response.json()
        return {"provider": "jira", "status": "connected", "mode": "official", "account": data.get("displayName")}
    def deliver(self, *, destination: str, payload: dict, idempotency_key: str) -> dict:
        description = {"type":"doc","version":1,"content":[{"type":"paragraph","content":[{"type":"text","text":payload["description"]}]}]}
        fields = {"project":{"key":destination},"issuetype":{"name":"Task"},"summary":payload["summary"],"description":description,"priority":{"name":payload.get("priority","High")},"labels":payload.get("labels",[])+[f"dias-{idempotency_key[:12]}"]}
        response = httpx.post(f"{self.base}/rest/api/3/issue", headers={"Authorization": f"Bearer {self.token}", "Accept":"application/json"}, json={"fields":fields}, timeout=30)
        response.raise_for_status(); data=response.json()
        return {"external_id":data["key"],"external_url":f"{self.base}/browse/{data['key']}"}


def delivery_adapter(provider: str) -> DeliveryAdapter:
    if settings.integrations_mode == "official":
        if provider == "slack" and settings.slack_bot_token: return SlackOfficialAdapter(settings.slack_bot_token)
        if provider == "jira" and settings.jira_access_token and settings.jira_cloud_id: return JiraOfficialAdapter(settings.jira_access_token, settings.jira_cloud_id)
        raise RuntimeError(f"{provider.title()} official credentials are not configured")
    return MockDeliveryAdapter(provider)


def integration_available(provider: str, verify: bool = True) -> bool:
    configured = settings.integrations_mode == "official" and (
        bool(settings.slack_bot_token) if provider == "slack"
        else bool(settings.jira_access_token and settings.jira_cloud_id) if provider == "jira"
        else False
    )
    if not configured or not verify:
        return configured
    try:
        delivery_adapter(provider).test()
        return True
    except Exception:
        return False


def slack_channel_label(channel_id: str) -> str:
    if not settings.slack_bot_token:
        return channel_id
    try:
        response = httpx.get("https://slack.com/api/conversations.info", headers={"Authorization": f"Bearer {settings.slack_bot_token}"}, params={"channel": channel_id}, timeout=20)
        response.raise_for_status();data=response.json()
        if data.get("ok") and data.get("channel", {}).get("name"):
            return data["channel"]["name"]
    except Exception:
        pass
    return channel_id
