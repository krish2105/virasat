"""Draft findings with the assessor model. Strict JSON, one retry with the parse error."""

from __future__ import annotations

from typing import Any, Literal

from langchain_core.language_models import BaseChatModel
from pydantic import BaseModel, ValidationError, field_validator

from virasat.agents import llm
from virasat.agents.state import AssessmentState


class FindingOut(BaseModel):
    claim: str
    clause_id: str
    evidence_ref: str
    severity: Literal["low", "medium", "high"]

    @field_validator("claim", "clause_id", "evidence_ref")
    @classmethod
    def _non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("must be non-empty")
        return v.strip()


class AssessOut(BaseModel):
    findings: list[FindingOut]


def _render(state: AssessmentState) -> str:
    clauses = "\n\n".join(
        f"[{c['clause_id']}] {c['path']}\n{c['text']}" for c in state["retrieved_clauses"]
    )
    feedback = ""
    if state["verifier_notes"]:
        feedback = (
            "VERIFIER FEEDBACK ON YOUR PREVIOUS DRAFT (fix every point):\n- "
            + "\n- ".join(state["verifier_notes"])
            + "\n"
        )
    return llm.prompt("assess").format(
        zone=state["zone"],
        change_type=state["change_type"],
        change_prob=f"{state['change_prob']:.2f}",
        epoch_before=state["epoch_before"],
        epoch_after=state["epoch_after"],
        facade_class=state["facade_class"] or "n/a",
        evidence_ref=state["evidence"]["after_crop_uri"],
        retrieved_clauses=clauses,
        verifier_feedback=feedback,
    )


def assess(state: AssessmentState, model: BaseChatModel | None = None) -> dict[str, Any]:
    text = _render(state)
    error = ""
    for _ in range(2):
        raw = llm.call(
            "assess",
            state["change_id"],
            text
            + (
                f"\n\nYour previous output was invalid: {error}\nReturn valid JSON only."
                if error
                else ""
            ),
            model,
        )
        try:
            out = AssessOut.model_validate(llm.extract_json(raw))
        except (ValidationError, ValueError) as exc:
            error = str(exc)[:500]
            continue
        return {"draft_findings": [f.model_dump() for f in out.findings]}
    return {
        "draft_findings": [],
        "errors": state["errors"] + [f"assess: invalid output twice: {error}"],
    }
