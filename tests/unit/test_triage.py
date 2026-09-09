from datetime import date

from virasat.agents.nodes.triage import triage
from virasat.agents.state import AssessmentState


def _state(**over: object) -> AssessmentState:
    base: dict[str, object] = dict(
        change_id="c1",
        tile_id="t1",
        centroid=(75.82, 26.92),
        zone="core",
        chowkri_id="Modikhana",
        epoch_before=date(2019, 12, 26),
        epoch_after=date(2025, 12, 4),
        change_prob=0.9,
        change_type="NEW_CONSTRUCTION",
        facade_class=None,
        evidence={"before_crop_uri": "b", "after_crop_uri": "a", "change_mask_uri": "m"},
        triage_decision=None,
        triage_reason=None,
        retrieved_clauses=[],
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


def test_outside_is_dropped() -> None:
    assert triage(_state(zone="outside"))["triage_decision"] == "drop"


def test_low_confidence_is_dropped() -> None:
    assert triage(_state(change_prob=0.4))["triage_decision"] == "drop"


def test_core_demolition_escalates_directly() -> None:
    out = triage(_state(change_type="DEMOLITION"))
    assert out["triage_decision"] == "escalate_direct"


def test_buffer_demolition_is_assessed() -> None:
    assert triage(_state(zone="buffer", change_type="DEMOLITION"))["triage_decision"] == "assess"


def test_default_is_assess() -> None:
    assert triage(_state())["triage_decision"] == "assess"
