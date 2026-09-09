"""Node and graph tests with a scripted fake model — no Ollama, no database."""

from __future__ import annotations

import json
from datetime import date
from typing import Any

import pytest
from langchain_core.language_models.fake_chat_models import FakeListChatModel

from virasat.agents import graph as graph_mod
from virasat.agents.nodes.assess import assess
from virasat.agents.nodes.route import decide
from virasat.agents.nodes.verify import mechanical_checks, verify
from virasat.agents.state import AssessmentState
from virasat.db.models import ChangeStatus

CLAUSES = [
    {
        "clause_id": "REG-10",
        "path": "Regulations > 10. Building Parameters",
        "text": "Height ...",
        "score": 1.0,
    },
    {
        "clause_id": "ACG-7",
        "path": "ACG > 7. New Construction",
        "text": "New construction ...",
        "score": 0.8,
    },
]


def state(**over: Any) -> AssessmentState:
    base: dict[str, Any] = dict(
        change_id="00000000-0000-0000-0000-000000000001",
        tile_id="t",
        centroid=(75.8, 26.9),
        zone="core",
        chowkri_id="Modikhana",
        epoch_before=date(2019, 12, 26),
        epoch_after=date(2025, 12, 4),
        change_prob=0.9,
        change_type="VERTICAL_ADDITION",
        facade_class=None,
        evidence={
            "before_crop_uri": "b.png",
            "after_crop_uri": "a.png",
            "change_mask_uri": "m.png",
        },
        triage_decision=None,
        triage_reason=None,
        retrieved_clauses=list(CLAUSES),
        draft_findings=[],
        verifier_verdict=None,
        verifier_notes=[],
        final_findings=[],
        routed_to=None,
        revision_count=0,
        errors=[],
    )
    base.update(over)
    return base  # type: ignore[return-value]


def finding(
    clause_id: str = "REG-10", claim: str = "An additional storey is visible."
) -> dict[str, str]:
    return {"claim": claim, "clause_id": clause_id, "evidence_ref": "a.png", "severity": "medium"}


def fake(*responses: object) -> FakeListChatModel:
    return FakeListChatModel(
        responses=[json.dumps(r) if not isinstance(r, str) else r for r in responses]
    )


def test_assess_parses_valid_json() -> None:
    out = assess(state(), fake({"findings": [finding()]}))
    assert out["draft_findings"][0]["clause_id"] == "REG-10"


def test_assess_retries_once_then_records_error() -> None:
    out = assess(state(), fake("not json", '{"findings": [{"claim": ""}]}'))
    assert out["draft_findings"] == []
    assert out["errors"][0].startswith("assess: invalid output twice")


def test_assess_empty_list_is_valid() -> None:
    assert assess(state(), fake({"findings": []}))["draft_findings"] == []


def test_mechanical_check_rejects_unretrieved_clause_and_enforcement() -> None:
    s = state(draft_findings=[finding("REG-99"), finding(claim="A penalty must be imposed.")])
    notes = mechanical_checks(s)
    assert any("not retrieved" in n for n in notes) and any("enforcement" in n for n in notes)


def test_mechanical_check_rejects_a_described_rather_than_referenced_evidence() -> None:
    """A prose description is not image evidence; hard rule 2 needs the actual crop."""
    s = state(draft_findings=[{**finding(), "evidence_ref": "visible in the after image"}])
    assert any("is not the supplied evidence" in n for n in mechanical_checks(s))


def test_verify_fails_mechanically_without_calling_model() -> None:
    out = verify(state(draft_findings=[finding("REG-99")]), fake())  # fake has no responses
    assert out["verifier_verdict"] == "fail" and out["revision_count"] == 1


def test_verify_pass_promotes_draft_to_final() -> None:
    s = state(draft_findings=[finding()])
    out = verify(s, fake({"verdict": "pass", "notes": [], "failing_finding_indices": []}))
    assert out["verifier_verdict"] == "pass" and out["final_findings"] == s["draft_findings"]


def test_graph_revision_loop_caps_at_two_and_routes_to_human() -> None:
    calls = {"assess": 0, "verify": 0}

    def assess_node(s: AssessmentState) -> dict[str, Any]:
        calls["assess"] += 1
        return {"draft_findings": [finding("REG-99")]}  # always cites an unretrieved clause

    def verify_node(s: AssessmentState) -> dict[str, Any]:
        calls["verify"] += 1
        return verify(s, fake())

    routed: list[tuple[str, ChangeStatus, str]] = []

    def route_node(s: AssessmentState) -> dict[str, Any]:
        routed.append(decide(s))
        return {"routed_to": routed[-1][0]}

    g = graph_mod.build_graph(
        retrieve_node=lambda s: {"retrieved_clauses": list(CLAUSES)},
        assess_node=assess_node,
        verify_node=verify_node,
        route_node=route_node,
    )
    final = g.invoke(state())
    assert calls["assess"] == 2 and calls["verify"] == 2
    assert final["revision_count"] == 2 and final["verifier_verdict"] == "fail"
    assert routed[-1][1] == ChangeStatus.needs_human_rewrite


def test_graph_drop_and_escalate_skip_llm_nodes() -> None:
    def boom(s: AssessmentState) -> dict[str, Any]:
        raise AssertionError("LLM node must not run")

    g = graph_mod.build_graph(
        retrieve_node=boom,
        assess_node=boom,
        verify_node=boom,
        route_node=lambda s: {"routed_to": decide(s)[0]},
    )
    assert g.invoke(state(zone="outside"))["routed_to"] == "dropped"
    out = g.invoke(state(change_type="DEMOLITION"))
    assert out["routed_to"] == "officer_queue" and decide(out)[2] == "urgent"


def test_graph_corpus_gap_routes_to_human() -> None:
    g = graph_mod.build_graph(
        retrieve_node=lambda s: {"retrieved_clauses": [], "errors": ["no applicable clause found"]},
        assess_node=lambda s: pytest.fail("must not assess on empty context"),
        route_node=lambda s: {"routed_to": decide(s)[0]},
    )
    out = g.invoke(state())
    assert decide(out)[1] == ChangeStatus.needs_human_rewrite
