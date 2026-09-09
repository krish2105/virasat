from __future__ import annotations

from collections.abc import Callable
from typing import Any

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from virasat.agents.nodes.assess import assess
from virasat.agents.nodes.retrieve import retrieve
from virasat.agents.nodes.route import route
from virasat.agents.nodes.triage import triage
from virasat.agents.nodes.verify import verify
from virasat.agents.state import AssessmentState
from virasat.settings import settings

MAX_REVISIONS = 2
Node = Callable[[AssessmentState], dict[str, Any]]


def build_graph(
    checkpointer: Any = None,
    *,
    retrieve_node: Node = retrieve,
    assess_node: Node = assess,
    verify_node: Node = verify,
    route_node: Node = route,
) -> CompiledStateGraph:
    g = StateGraph(AssessmentState)
    g.add_node("triage", triage)
    g.add_node("retrieve", retrieve_node)
    g.add_node("assess", assess_node)
    g.add_node("verify", verify_node)
    g.add_node("route", route_node)

    g.add_edge(START, "triage")
    g.add_conditional_edges(
        "triage",
        lambda s: s["triage_decision"],
        {"assess": "retrieve", "drop": "route", "escalate_direct": "route"},
    )
    # A corpus gap is routed to a human, never assessed against an empty context.
    g.add_conditional_edges(
        "retrieve",
        lambda s: "assess" if s["retrieved_clauses"] else "route",
        {"assess": "assess", "route": "route"},
    )
    g.add_edge("assess", "verify")
    g.add_conditional_edges(
        "verify",
        lambda s: "assess"
        if (s["verifier_verdict"] == "fail" and s["revision_count"] < MAX_REVISIONS)
        else "route",
        {"assess": "assess", "route": "route"},
    )
    g.add_edge("route", END)
    return g.compile(checkpointer=checkpointer)


def postgres_checkpointer() -> Any:
    from langgraph.checkpoint.postgres import PostgresSaver

    dsn = settings.database_url.replace("postgresql+psycopg://", "postgresql://")
    saver = PostgresSaver.from_conn_string(dsn)
    return saver
