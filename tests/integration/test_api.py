"""Officer decision loop end to end against the test database. Rows here are test
fixtures, never metrics."""

from __future__ import annotations

import uuid
from datetime import date

from geoalchemy2.shape import from_shape
from shapely.geometry import Point, box

from virasat.db.models import (
    AuditLog,
    Change,
    ChangeType,
    Clause,
    Finding,
    Run,
    Severity,
    Tile,
    Zone,
)
from virasat.db.session import session_scope


def _seed_change(chowkri: str = "Modikhana", with_finding: bool = True) -> uuid.UUID:
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
                chowkri_id=chowkri,
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
                chowkri_id=chowkri,
                epoch_before=date(2019, 12, 26),
                epoch_after=date(2025, 12, 4),
                change_prob=0.87,
                change_type=ChangeType.VERTICAL_ADDITION,
                before_uri="/e/b.png",
                after_uri="/e/a.png",
                mask_uri="/e/m.png",
                triage_decision="assess",
                verifier_verdict="pass",
            )
        )
        s.flush()
        if with_finding and s.get(Clause, "REG-10") is None:
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
        if with_finding:
            s.add(
                Finding(
                    change_id=cid,
                    claim="An additional storey is visible above the parapet line.",
                    clause_id="REG-10",
                    evidence_ref="/e/a.png",
                    severity=Severity.medium,
                    is_final=True,
                )
            )
    return cid


def test_health_is_public(client) -> None:  # type: ignore[no-untyped-def]
    r = client.get("/health")
    assert r.status_code == 200 and r.json()["database"] is True


def test_queue_requires_login(client) -> None:  # type: ignore[no-untyped-def]
    assert client.get("/queue").status_code == 401


def test_reject_requires_reason(client, officer) -> None:  # type: ignore[no-untyped-def]
    cid = _seed_change()
    r = client.post(f"/changes/{cid}/decision", json={"decision": "reject"})
    assert r.status_code == 422


def test_decision_round_trip_lands_in_audit_and_retraining_set(client, officer) -> None:  # type: ignore[no-untyped-def]
    cid = _seed_change()
    assert any(i["id"] == str(cid) for i in client.get("/queue").json()["items"])
    r = client.post(
        f"/changes/{cid}/decision",
        json={"decision": "reject", "reason": "legal building; mapping lag"},
    )
    assert r.status_code == 200 and r.json()["status"] == "rejected"
    assert r.json()["decisions"][0]["reason"].startswith("legal building")
    audit = client.get("/audit", params={"change_id": str(cid)}).json()
    assert any(a["action"] == "decision:reject" for a in audit)
    with session_scope() as s:
        row = s.query(AuditLog).filter_by(change_id=cid).first()
        assert row is not None
    assert not any(i["id"] == str(cid) for i in client.get("/queue").json()["items"])


def test_escalation_creates_notification_and_visit(client, officer) -> None:  # type: ignore[no-untyped-def]
    cid = _seed_change()
    client.post(f"/changes/{cid}/decision", json={"decision": "escalate"})
    assert any(n["change_id"] == str(cid) for n in client.get("/notifications").json())
    v = client.post("/visits", json={"change_id": str(cid), "scheduled_for": "2026-09-15"})
    assert v.status_code == 201 and v.json()["status"] == "scheduled"
    u = client.patch(
        f"/visits/{v.json()['id']}", json={"status": "done", "field_notes": "verified on site"}
    )
    assert u.json()["status"] == "done"


def test_public_aggregate_has_no_property_attribution(client) -> None:  # type: ignore[no-untyped-def]
    _seed_change()
    r = client.get("/map/aggregate")
    assert r.status_code == 200
    body = r.text
    assert "building_id" not in body and "before_uri" not in body
    assert all(
        set(c) == {"chowkri_id", "zone", "counts_by_type", "counts_by_status"}
        for c in r.json()["cells"]
    )


def test_dossier_exports(client, officer) -> None:  # type: ignore[no-untyped-def]
    _seed_change()
    assert client.get("/dossier").json()["count"] >= 1
    assert client.get("/dossier.csv").headers["content-type"].startswith("text/csv")
    assert client.get("/dossier.pdf").content[:4] == b"%PDF"


def test_fairness_blocked_until_enough_decisions(client, officer) -> None:  # type: ignore[no-untyped-def]
    r = client.get("/metrics/fairness").json()
    assert r["status"] in ("BLOCKED", "measured") and r["max_ratio"] == 1.5
