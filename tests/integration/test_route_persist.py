"""`route` persistence. A finding may only cite a clause that was actually retrieved;
anything else is model output, not a citation, and must never reach the findings table."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Any

from geoalchemy2.shape import from_shape
from shapely.geometry import Point, box

from virasat.agents.nodes.route import route
from virasat.db.models import (
    AuditLog,
    Change,
    ChangeStatus,
    ChangeType,
    Clause,
    Finding,
    Run,
    Tile,
    Zone,
)
from virasat.db.session import session_scope

HALLUCINATED = (
    "Jaipur Heritage Conservation and Protection Regulations 2020, Clause 10.3.2 (b) (iii)"
)


def _seed() -> uuid.UUID:
    with session_scope() as s:
        run = Run(
            epoch_before=date(2019, 12, 26),
            epoch_after=date(2025, 12, 4),
            git_sha="test",
            config_hash="t",
        )
        s.add(run)
        s.flush()
        tile_id = f"t-{uuid.uuid4().hex[:6]}"
        s.add(
            Tile(
                id=tile_id,
                geom=from_shape(box(581000, 2977000, 581320, 2977320), srid=32643),
                centroid_lon=75.82,
                centroid_lat=26.92,
                zone=Zone.core,
                chowkri_id="Modikhana",
            )
        )
        if s.get(Clause, "REG-10") is None:
            s.add(
                Clause(
                    id="REG-10",
                    regulation="test fixture",
                    section="10",
                    clause="10",
                    path="test fixture > 10. Building Parameters",
                    text="fixture clause text",
                    applies_to_zone=["core"],
                    applies_to_change_type=["VERTICAL_ADDITION"],
                    source_page=14,
                    source_doc_sha256="fixture",
                )
            )
        s.flush()
        cid = uuid.uuid4()
        s.add(
            Change(
                id=cid,
                run_id=run.id,
                tile_id=tile_id,
                geom=from_shape(Point(581100, 2977100), srid=32643),
                zone=Zone.core,
                chowkri_id="Modikhana",
                epoch_before=date(2019, 12, 26),
                epoch_after=date(2025, 12, 4),
                change_prob=0.87,
                change_type=ChangeType.VERTICAL_ADDITION,
                before_uri="/e/b.png",
                after_uri="/e/a.png",
                mask_uri="/e/m.png",
            )
        )
    return cid


def _state(cid: uuid.UUID, **over: Any) -> Any:
    base: dict[str, Any] = dict(
        change_id=str(cid),
        tile_id="t",
        centroid=(75.8, 26.9),
        zone="core",
        chowkri_id="Modikhana",
        epoch_before=date(2019, 12, 26),
        epoch_after=date(2025, 12, 4),
        change_prob=0.87,
        change_type="VERTICAL_ADDITION",
        facade_class=None,
        evidence={
            "before_crop_uri": "b.png",
            "after_crop_uri": "a.png",
            "change_mask_uri": "m.png",
        },
        triage_decision="assess",
        triage_reason=None,
        retrieved_clauses=[{"clause_id": "REG-10", "path": "p", "text": "t", "score": 1.0}],
        draft_findings=[],
        verifier_verdict=None,
        verifier_notes=[],
        final_findings=[],
        routed_to=None,
        revision_count=0,
        errors=[],
    )
    base.update(over)
    return base


def _finding(clause_id: str) -> dict[str, str]:
    return {
        "claim": "An additional storey is visible above the parapet line.",
        "clause_id": clause_id,
        "evidence_ref": "a.png",
        "severity": "medium",
    }


def test_route_does_not_persist_a_finding_citing_an_unretrieved_clause() -> None:
    """The failing draft path: two revisions burnt, drafts cite a clause the model invented."""
    cid = _seed()
    route(
        _state(
            cid,
            draft_findings=[_finding(HALLUCINATED), _finding("REG-10")],
            verifier_verdict="fail",
            verifier_notes=[f"finding 0: cites {HALLUCINATED} which was not retrieved"],
            revision_count=2,
        )
    )
    with session_scope() as s:
        rows = s.query(Finding).filter_by(change_id=cid).all()
        assert [r.clause_id for r in rows] == ["REG-10"]
        assert all(r.is_final is False for r in rows)
        change = s.get(Change, cid)
        assert change is not None and change.status == ChangeStatus.needs_human_rewrite
        audit = s.query(AuditLog).filter_by(change_id=cid).one()
        rejected = audit.payload["rejected_findings"]
        assert len(rejected) == 1 and rejected[0]["clause_id"] == HALLUCINATED


def test_route_persists_verified_findings_as_final() -> None:
    cid = _seed()
    route(
        _state(
            cid,
            draft_findings=[_finding("REG-10")],
            final_findings=[_finding("REG-10")],
            verifier_verdict="pass",
        )
    )
    with session_scope() as s:
        rows = s.query(Finding).filter_by(change_id=cid).all()
        assert len(rows) == 1 and rows[0].is_final is True
        assert s.query(AuditLog).filter_by(change_id=cid).one().payload["rejected_findings"] == []
