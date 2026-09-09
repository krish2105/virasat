"""Terminal node. Writes the outcome to Postgres and the append-only audit log."""

from __future__ import annotations

import subprocess
import uuid
from typing import Any

from virasat.agents import llm
from virasat.agents.state import AssessmentState
from virasat.db.models import AuditLog, Change, ChangeStatus, Finding, Severity
from virasat.db.session import session_scope
from virasat.llm.router import model_spec

PRIORITY = {"high": "high", "medium": "normal", "low": "low"}


def git_sha() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return "unknown"


def decide(state: AssessmentState) -> tuple[str, ChangeStatus, str]:
    """(routed_to, status, priority) without touching the database."""
    if state["triage_decision"] == "drop":
        return "dropped", ChangeStatus.dropped, "none"
    if state["triage_decision"] == "escalate_direct":
        return "officer_queue", ChangeStatus.escalated, "urgent"
    if state["errors"] and not state["retrieved_clauses"]:
        return "officer_queue", ChangeStatus.needs_human_rewrite, "normal"
    if state["verifier_verdict"] == "pass":
        sev = max(
            (f["severity"] for f in state["final_findings"]),
            default="low",
            key=["low", "medium", "high"].index,
        )
        return "officer_queue", ChangeStatus.pending, PRIORITY[sev]
    return "officer_queue", ChangeStatus.needs_human_rewrite, "normal"


def route(state: AssessmentState) -> dict[str, Any]:
    routed_to, status, priority = decide(state)
    findings = (
        state["final_findings"] if status == ChangeStatus.pending else state["draft_findings"]
    )
    with session_scope() as s:
        change = s.get(Change, uuid.UUID(state["change_id"]))
        if change is not None:
            change.status = status
            change.priority = priority
            change.triage_decision = state["triage_decision"]
            change.triage_reason = state["triage_reason"]
            change.verifier_verdict = state["verifier_verdict"]
            change.verifier_notes = list(state["verifier_notes"])
            change.revision_count = state["revision_count"]
            for f in findings:
                s.add(
                    Finding(
                        change_id=change.id,
                        claim=f["claim"],
                        clause_id=f["clause_id"],
                        evidence_ref=f["evidence_ref"],
                        severity=Severity(f["severity"]),
                        revision=state["revision_count"],
                        is_final=status == ChangeStatus.pending,
                    )
                )
        s.add(
            AuditLog(
                actor="system:agents",
                action=f"route:{status.value}",
                change_id=uuid.UUID(state["change_id"]),
                payload={
                    "routed_to": routed_to,
                    "priority": priority,
                    "triage": state["triage_reason"],
                    "errors": list(state["errors"]),
                    "verifier_notes": list(state["verifier_notes"]),
                },
                git_sha=git_sha(),
                model_ids={n: model_spec(n)["model"] for n in ("assess", "verify")},
                prompt_versions=dict(llm.PROMPT_VERSIONS),
                total_tokens=llm.TOKENS.pop(state["change_id"], 0),
            )
        )
    return {"routed_to": routed_to}
