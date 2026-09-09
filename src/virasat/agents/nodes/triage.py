"""Cheap deterministic filter. No model: the decision is a threshold check."""

from virasat.agents.state import AssessmentState

CONFIDENCE_FLOOR = 0.55


def triage(state: AssessmentState) -> dict[str, str]:
    """Decide whether this change is worth assessing. Returns only the keys it sets."""
    if state["zone"] == "outside":
        return {"triage_decision": "drop", "triage_reason": "outside inscribed area"}
    if state["change_prob"] < CONFIDENCE_FLOOR:
        return {"triage_decision": "drop", "triage_reason": "below confidence floor"}
    if state["change_type"] == "DEMOLITION" and state["zone"] == "core":
        # Irreversible; a 20-minute assessment delay can matter. Straight to a human.
        return {
            "triage_decision": "escalate_direct",
            "triage_reason": "irreversible change in core zone",
        }
    return {"triage_decision": "assess", "triage_reason": "meets assessment criteria"}
