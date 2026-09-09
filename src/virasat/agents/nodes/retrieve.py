"""Clause retrieval with the metadata pre-filter. No LLM."""

from __future__ import annotations

from typing import Any

from virasat.agents.state import AssessmentState
from virasat.rag.retrieve import hybrid_search


def query_for(state: AssessmentState) -> str:
    what = state["change_type"].replace("_", " ").lower()
    facade = f", facade {state['facade_class'].lower()}" if state["facade_class"] else ""
    return (
        f"{what} detected in the {state['zone']} zone{facade} between "
        f"{state['epoch_before']:%Y} and {state['epoch_after']:%Y}"
    )


def retrieve(state: AssessmentState) -> dict[str, Any]:
    hits = hybrid_search(query_for(state), state["zone"], state["change_type"], k=5)
    clauses = [
        {"clause_id": h.clause_id, "path": h.path, "text": h.text, "score": h.score} for h in hits
    ]
    if not clauses:
        return {
            "retrieved_clauses": [],
            "errors": state["errors"] + ["no applicable clause found — possible corpus gap"],
        }
    return {"retrieved_clauses": clauses}
