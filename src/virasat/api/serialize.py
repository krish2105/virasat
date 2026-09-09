from __future__ import annotations

import uuid

from geoalchemy2.shape import to_shape
from pyproj import Transformer
from sqlalchemy import select
from sqlalchemy.orm import Session

from virasat.api import schemas
from virasat.db.models import Change, Clause, Finding, Officer, OfficerDecision, SiteVisit

_to_wgs = Transformer.from_crs("EPSG:32643", "EPSG:4326", always_xy=True)
SEVERITY_ORDER = ["low", "medium", "high"]


def top_severity(findings: list[Finding]) -> str | None:
    final = [f.severity.value for f in findings if f.is_final] or [
        f.severity.value for f in findings
    ]
    return max(final, key=SEVERITY_ORDER.index) if final else None


def change_summary(c: Change, findings: list[Finding]) -> schemas.ChangeSummary:
    return schemas.ChangeSummary(
        id=c.id,
        building_id=c.building_id,
        zone=c.zone.value,
        chowkri_id=c.chowkri_id,
        change_type=c.change_type.value,
        change_prob=c.change_prob,
        calibration_date=c.calibration_date,
        status=c.status.value,
        priority=c.priority,
        epoch_before=c.epoch_before,
        epoch_after=c.epoch_after,
        severity=top_severity(findings),
        created_at=c.created_at,
    )


def decision_out(d: OfficerDecision, officers: dict[uuid.UUID, Officer]) -> schemas.DecisionOut:
    o = officers.get(d.officer_id)
    return schemas.DecisionOut(
        id=d.id,
        change_id=d.change_id,
        officer_id=d.officer_id,
        officer_name=o.display_name if o else "?",
        decision=d.decision.value,
        reason=d.reason,
        created_at=d.created_at,
    )


def change_detail(db: Session, c: Change) -> schemas.ChangeDetail:
    findings = list(db.scalars(select(Finding).where(Finding.change_id == c.id)))
    clause_ids = {f.clause_id for f in findings}
    clauses = (
        list(db.scalars(select(Clause).where(Clause.id.in_(clause_ids)))) if clause_ids else []
    )
    decisions = list(
        db.scalars(
            select(OfficerDecision)
            .where(OfficerDecision.change_id == c.id)
            .order_by(OfficerDecision.created_at)
        )
    )
    officers = {o.id: o for o in db.scalars(select(Officer))}
    pt = to_shape(c.geom)  # type: ignore[arg-type]
    lon, lat = _to_wgs.transform(pt.x, pt.y)
    return schemas.ChangeDetail(
        **change_summary(c, findings).model_dump(),
        facade_class=c.facade_class,
        before_uri=c.before_uri,
        after_uri=c.after_uri,
        mask_uri=c.mask_uri,
        triage_decision=c.triage_decision,
        triage_reason=c.triage_reason,
        verifier_verdict=c.verifier_verdict,
        verifier_notes=list(c.verifier_notes),
        revision_count=c.revision_count,
        findings=[
            schemas.FindingOut(
                id=f.id,
                claim=f.claim,
                clause_id=f.clause_id,
                evidence_ref=f.evidence_ref,
                severity=f.severity.value,
                is_final=f.is_final,
            )
            for f in findings
        ],
        clauses=[
            schemas.ClauseOut(clause_id=k.id, path=k.path, text=k.text, source_page=k.source_page)
            for k in clauses
        ],
        decisions=[decision_out(d, officers) for d in decisions],
        centroid=(round(lon, 6), round(lat, 6)),
    )


def visit_out(db: Session, v: SiteVisit) -> schemas.VisitOut:
    c = db.get(Change, v.change_id)
    assert c is not None
    findings = list(db.scalars(select(Finding).where(Finding.change_id == c.id)))
    assignee = db.get(Officer, v.assignee_id) if v.assignee_id else None
    return schemas.VisitOut(
        id=v.id,
        change_id=v.change_id,
        scheduled_for=v.scheduled_for,
        assignee_id=v.assignee_id,
        assignee_name=assignee.display_name if assignee else None,
        status=v.status.value,
        field_notes=v.field_notes,
        change=change_summary(c, findings),
    )
