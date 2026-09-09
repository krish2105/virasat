from datetime import date
from typing import Literal, TypedDict


class Evidence(TypedDict):
    before_crop_uri: str
    after_crop_uri: str
    change_mask_uri: str


class Clause(TypedDict):
    clause_id: str
    path: str
    text: str
    score: float


class Finding(TypedDict):
    claim: str  # one sentence, one assertion
    clause_id: str  # MUST be non-empty
    evidence_ref: str  # MUST be non-empty
    severity: Literal["low", "medium", "high"]


class AssessmentState(TypedDict):
    # --- inputs (set by the pipeline, never by a model) ---
    change_id: str
    tile_id: str
    centroid: tuple[float, float]
    zone: Literal["core", "buffer", "outside"]
    chowkri_id: str
    epoch_before: date
    epoch_after: date
    change_prob: float  # calibrated
    change_type: str
    facade_class: str | None
    evidence: Evidence

    # --- populated by nodes ---
    triage_decision: Literal["assess", "drop", "escalate_direct"] | None
    triage_reason: str | None
    retrieved_clauses: list[Clause]
    draft_findings: list[Finding]
    verifier_verdict: Literal["pass", "fail"] | None
    verifier_notes: list[str]
    final_findings: list[Finding]
    routed_to: str | None

    # --- control ---
    revision_count: int  # hard cap 2
    errors: list[str]
