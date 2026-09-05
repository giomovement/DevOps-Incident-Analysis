from typing import Any, Literal, TypedDict
from pydantic import BaseModel, EmailStr, Field


Role = Literal["admin", "responder", "viewer"]


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)
    display_name: str = Field(min_length=2, max_length=80)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class IncidentCreate(BaseModel):
    title: str = Field(min_length=3, max_length=160)
    description: str | None = Field(default=None, max_length=4000)
    service: str | None = Field(default=None, max_length=120)
    environment: str | None = Field(default=None, max_length=80)
    deployment: str | None = Field(default=None, max_length=120)


class ActionDecision(BaseModel):
    comment: str | None = Field(default=None, max_length=1000)
    payload_hash: str


class ChatRequest(BaseModel):
    content: str = Field(min_length=2, max_length=4000)


class IncidentState(TypedDict, total=False):
    schema_version: str
    workspace_id: str
    incident_id: str
    run_id: str
    langgraph_thread_id: str
    file_manifest: list[dict[str, Any]]
    incident_context: dict[str, Any]
    status: str
    current_phase: str
    completed_nodes: list[str]
    cancel_requested: bool
    event_refs: list[str]
    evidence_refs: list[str]
    correlation_groups: list[dict[str, Any]]
    findings: list[dict[str, Any]]
    recommendations: list[dict[str, Any]]
    slack_drafts: list[dict[str, Any]]
    jira_drafts: list[dict[str, Any]]
    cookbook_ref: str | None
    errors: list[dict[str, Any]]
    warnings: list[str]
