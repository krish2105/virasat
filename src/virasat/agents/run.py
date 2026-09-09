"""`uv run agents` — run the assessment graph over pending changes, checkpointed in Postgres."""

from __future__ import annotations

import argparse
from typing import Any

import structlog
from langchain_core.runnables import RunnableConfig
from sqlalchemy import select

from virasat.agents.graph import build_graph, postgres_checkpointer
from virasat.db.models import Change, ChangeStatus
from virasat.db.session import session_scope
from virasat.llm.router import assert_distinct_families, mode, model_spec

log = structlog.get_logger()


def initial_state(c: Change) -> dict[str, Any]:
    return {
        "change_id": str(c.id),
        "tile_id": c.tile_id,
        "centroid": (0.0, 0.0),  # geometry lives in Postgres; nodes do not need it
        "zone": c.zone.value,
        "chowkri_id": c.chowkri_id or "",
        "epoch_before": c.epoch_before,
        "epoch_after": c.epoch_after,
        "change_prob": c.change_prob,
        "change_type": c.change_type.value,
        "facade_class": c.facade_class,
        "evidence": {
            "before_crop_uri": c.before_uri,
            "after_crop_uri": c.after_uri,
            "change_mask_uri": c.mask_uri,
        },
        "triage_decision": None,
        "triage_reason": None,
        "retrieved_clauses": [],
        "draft_findings": [],
        "verifier_verdict": None,
        "verifier_notes": [],
        "final_findings": [],
        "routed_to": None,
        "revision_count": 0,
        "errors": [],
    }


def main() -> None:
    parser = argparse.ArgumentParser(prog="agents")
    parser.add_argument("--limit", type=int, default=50)
    args = parser.parse_args()
    assert_distinct_families()
    log.info(
        "agents_start",
        mode=mode(),
        assess=model_spec("assess")["model"],
        verify=model_spec("verify")["model"],
    )

    with session_scope() as s:
        pending = list(
            s.scalars(
                select(Change)
                .where(Change.status == ChangeStatus.pending, Change.triage_decision.is_(None))
                .limit(args.limit)
            )
        )
    if not pending:
        print("agents: no pending changes")
        return
    with postgres_checkpointer() as saver:
        saver.setup()
        graph = build_graph(saver)
        for c in pending:
            cfg: RunnableConfig = {"configurable": {"thread_id": str(c.id)}}
            out = graph.invoke(initial_state(c), config=cfg)
            log.info(
                "agents_done",
                change_id=str(c.id),
                routed_to=out["routed_to"],
                verdict=out["verifier_verdict"],
                revisions=out["revision_count"],
            )
    print(f"agents: processed {len(pending)} changes")


if __name__ == "__main__":
    main()
