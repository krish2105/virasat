from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Health(BaseModel):
    status: Literal["ok", "degraded"]
    database: bool
    ollama: bool
    models: dict[str, str]
    mode: str


class LoginIn(BaseModel):
    username: str
    password: str


class OfficerOut(BaseModel):
    id: uuid.UUID
    username: str
    display_name: str
    role: str
    locale: str


class ClauseOut(BaseModel):
    clause_id: str
    path: str
    text: str
    source_page: int


class FindingOut(BaseModel):
    id: uuid.UUID
    claim: str
    clause_id: str
    evidence_ref: str
    severity: str
    is_final: bool


class ChangeSummary(BaseModel):
    id: uuid.UUID
    building_id: str | None
    zone: str
    chowkri_id: str | None
    change_type: str
    change_prob: float
    calibration_date: date | None
    status: str
    priority: str
    epoch_before: date
    epoch_after: date
    severity: str | None
    created_at: datetime


class ChangeDetail(ChangeSummary):
    facade_class: str | None
    before_uri: str
    after_uri: str
    mask_uri: str
    triage_decision: str | None
    triage_reason: str | None
    verifier_verdict: str | None
    verifier_notes: list[str]
    revision_count: int
    findings: list[FindingOut]
    clauses: list[ClauseOut]
    decisions: list[DecisionOut]
    centroid: tuple[float, float]


class DecisionIn(BaseModel):
    decision: Literal["approve", "reject", "escalate"]
    reason: str | None = None

    @model_validator(mode="after")
    def _reject_needs_reason(self) -> DecisionIn:
        if self.decision == "reject" and not (self.reason or "").strip():
            raise ValueError("a rejection needs a reason — it feeds the retraining set")
        return self


class DecisionOut(BaseModel):
    id: uuid.UUID
    change_id: uuid.UUID
    officer_id: uuid.UUID
    officer_name: str
    decision: str
    reason: str | None
    created_at: datetime


class QueuePage(BaseModel):
    items: list[ChangeSummary]
    total: int


class RunIn(BaseModel):
    epoch_before: date
    epoch_after: date


class RunOut(BaseModel):
    id: uuid.UUID
    status: str
    started_at: datetime
    finished_at: datetime | None
    epoch_before: date
    epoch_after: date
    git_sha: str
    total_tokens: int
    progress: dict[str, object]


class FairnessOut(BaseModel):
    status: Literal["measured", "BLOCKED"]
    reason: str | None = None
    fpr_by_chowkri: dict[str, float] = Field(default_factory=dict)
    n_by_chowkri: dict[str, int] = Field(default_factory=dict)
    disparity_ratio: float | None = None
    max_ratio: float
    passes: bool | None = None


class AggregateCell(BaseModel):
    chowkri_id: str
    zone: str
    counts_by_type: dict[str, int]
    counts_by_status: dict[str, int]


class AggregateOut(BaseModel):
    cells: list[AggregateCell]
    window: tuple[date, date] | None
    attribution: str = (
        "© OpenStreetMap contributors (ODbL); UNESCO WHC 1605; Google Open Buildings (CC BY 4.0)"
    )


class AuditRow(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    id: int
    ts: datetime
    actor: str
    action: str
    change_id: uuid.UUID | None
    payload: dict[str, object]
    git_sha: str | None
    model_ids: dict[str, object]
    prompt_versions: dict[str, object]
    total_tokens: int


class TimelineEntry(BaseModel):
    change: ChangeSummary
    decisions: list[DecisionOut]


class BuildingTimeline(BaseModel):
    building_id: str
    zone: str
    chowkri_id: str | None
    entries: list[TimelineEntry]


class VisitIn(BaseModel):
    change_id: uuid.UUID
    scheduled_for: date
    assignee_id: uuid.UUID | None = None


class VisitUpdate(BaseModel):
    status: Literal["scheduled", "done", "cancelled"] | None = None
    field_notes: str | None = None
    scheduled_for: date | None = None
    assignee_id: uuid.UUID | None = None


class VisitOut(BaseModel):
    id: uuid.UUID
    change_id: uuid.UUID
    scheduled_for: date
    assignee_id: uuid.UUID | None
    assignee_name: str | None
    status: str
    field_notes: str | None
    change: ChangeSummary


class NotificationOut(BaseModel):
    id: uuid.UUID
    kind: str
    title: str
    body: str
    change_id: uuid.UUID | None
    created_at: datetime
    read_at: datetime | None


class HealthMetrics(BaseModel):
    pipeline: dict[str, object] | None
    calibration: dict[str, object] | None
    retrieval: dict[str, object]
    fairness: FairnessOut
    queue: dict[str, int]
    runs: list[RunOut]
    agreement_rate: float | None
