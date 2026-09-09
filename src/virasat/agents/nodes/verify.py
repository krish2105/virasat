"""Adversarial check on a separate model. Mechanical rules run first; the model then
attacks what is left. A finding never passes on the assessor's say-so."""

from __future__ import annotations

from typing import Any, Literal

from langchain_core.language_models import BaseChatModel
from pydantic import BaseModel, ValidationError, model_validator

from virasat.agents import llm
from virasat.agents.state import AssessmentState

ENFORCEMENT = (
    "penalt",
    "prosecut",
    "notice",
    "demolish the",
    "fine ",
    "seal",
    "legal action",
    "must be removed",
)


class VerifyOut(BaseModel):
    verdict: Literal["pass", "fail"]
    notes: list[str]
    failing_finding_indices: list[int]

    @model_validator(mode="after")
    def _fail_must_name_a_finding(self) -> VerifyOut:
        """A rejection that names nothing is incoherent, not a rejection. The retry
        loop asks again rather than letting the draft through on a shapeless verdict."""
        if self.verdict == "fail" and not self.failing_finding_indices:
            raise ValueError("verdict 'fail' requires at least one failing_finding_index")
        return self


def mechanical_checks(state: AssessmentState) -> list[str]:
    allowed = {c["clause_id"] for c in state["retrieved_clauses"]}
    evidence = state["evidence"]["after_crop_uri"]
    notes = []
    for i, f in enumerate(state["draft_findings"]):
        if f["clause_id"] not in allowed:
            notes.append(f"finding {i}: cites {f['clause_id']} which was not retrieved")
        if f["evidence_ref"] != evidence:
            notes.append(
                f"finding {i}: evidence_ref {f['evidence_ref']!r} is not the supplied "
                f"evidence {evidence!r}"
            )
        if any(k in f["claim"].lower() for k in ENFORCEMENT):
            notes.append(f"finding {i}: recommends enforcement")
    return notes


def verify(state: AssessmentState, model: BaseChatModel | None = None) -> dict[str, Any]:
    if any(e.startswith("assess:") for e in state["errors"]):
        return {
            "verifier_verdict": "fail",
            "verifier_notes": ["assessor produced no valid draft"],
            "revision_count": 2,
        }
    if not state["draft_findings"]:
        return {"verifier_verdict": "pass", "verifier_notes": ["empty draft: nothing to verify"]}
    notes = mechanical_checks(state)
    if notes:
        return {
            "verifier_verdict": "fail",
            "verifier_notes": notes,
            "revision_count": state["revision_count"] + 1,
        }

    text = llm.prompt("verify").format(
        retrieved_clauses="\n\n".join(
            f"[{c['clause_id']}] {c['path']}\n{c['text']}" for c in state["retrieved_clauses"]
        ),
        evidence_ref=state["evidence"]["after_crop_uri"],
        draft_findings="\n".join(f"{i}. {f}" for i, f in enumerate(state["draft_findings"])),
    )
    error = ""
    for _ in range(2):
        raw = llm.call(
            "verify",
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
            out = VerifyOut.model_validate(llm.extract_json(raw))
        except (ValidationError, ValueError) as exc:
            error = str(exc)[:500]
            continue
        if out.verdict == "pass":
            return {
                "verifier_verdict": "pass",
                "verifier_notes": out.notes,
                "final_findings": state["draft_findings"],
            }
        return {
            "verifier_verdict": "fail",
            "verifier_notes": out.notes or ["verifier failed the draft"],
            "revision_count": state["revision_count"] + 1,
        }
    return {
        "verifier_verdict": "fail",
        "verifier_notes": [f"verifier output invalid twice: {error}"],
        "revision_count": state["revision_count"] + 1,
    }
