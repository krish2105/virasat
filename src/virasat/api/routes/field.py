"""Per-building timeline, site-visit scheduler, notifications."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from virasat.api import schemas
from virasat.api.deps import current_officer, get_db
from virasat.api.serialize import change_summary, decision_out, visit_out
from virasat.db.models import (
    AuditLog,
    Building,
    Change,
    Finding,
    Notification,
    Officer,
    OfficerDecision,
    SiteVisit,
    VisitStatus,
)

router = APIRouter(tags=["field"])


@router.get("/buildings/{building_id}/timeline", response_model=schemas.BuildingTimeline)
def timeline(
    building_id: str, db: Session = Depends(get_db), officer: Officer = Depends(current_officer)
) -> schemas.BuildingTimeline:
    b = db.get(Building, building_id)
    if b is None:
        raise HTTPException(404, "building not found")
    changes = list(
        db.scalars(
            select(Change).where(Change.building_id == building_id).order_by(Change.epoch_after)
        )
    )
    officers = {o.id: o for o in db.scalars(select(Officer))}
    entries = []
    for c in changes:
        findings = list(db.scalars(select(Finding).where(Finding.change_id == c.id)))
        decisions = list(
            db.scalars(select(OfficerDecision).where(OfficerDecision.change_id == c.id))
        )
        entries.append(
            schemas.TimelineEntry(
                change=change_summary(c, findings),
                decisions=[decision_out(d, officers) for d in decisions],
            )
        )
    return schemas.BuildingTimeline(
        building_id=b.id, zone=b.zone.value, chowkri_id=b.chowkri_id, entries=entries
    )


@router.get("/visits", response_model=list[schemas.VisitOut])
def visits(
    status: str | None = None,
    db: Session = Depends(get_db),
    officer: Officer = Depends(current_officer),
) -> list[schemas.VisitOut]:
    q = select(SiteVisit).order_by(SiteVisit.scheduled_for)
    if status:
        q = q.where(SiteVisit.status == VisitStatus(status))
    return [visit_out(db, v) for v in db.scalars(q)]


@router.post("/visits", response_model=schemas.VisitOut, status_code=201)
def create_visit(
    body: schemas.VisitIn,
    db: Session = Depends(get_db),
    officer: Officer = Depends(current_officer),
) -> schemas.VisitOut:
    if db.get(Change, body.change_id) is None:
        raise HTTPException(404, "change not found")
    v = SiteVisit(
        change_id=body.change_id,
        scheduled_for=body.scheduled_for,
        assignee_id=body.assignee_id or officer.id,
    )
    db.add(v)
    db.add(
        AuditLog(
            actor=f"officer:{officer.username}",
            action="visit:scheduled",
            change_id=body.change_id,
            payload={"scheduled_for": body.scheduled_for.isoformat()},
        )
    )
    db.flush()
    return visit_out(db, v)


@router.patch("/visits/{visit_id}", response_model=schemas.VisitOut)
def update_visit(
    visit_id: uuid.UUID,
    body: schemas.VisitUpdate,
    db: Session = Depends(get_db),
    officer: Officer = Depends(current_officer),
) -> schemas.VisitOut:
    v = db.get(SiteVisit, visit_id)
    if v is None:
        raise HTTPException(404, "visit not found")
    for k, val in body.model_dump(exclude_none=True).items():
        setattr(v, k, VisitStatus(val) if k == "status" else val)
    db.add(
        AuditLog(
            actor=f"officer:{officer.username}",
            action="visit:updated",
            change_id=v.change_id,
            payload=body.model_dump(mode="json", exclude_none=True),
        )
    )
    db.flush()
    return visit_out(db, v)


@router.get("/notifications", response_model=list[schemas.NotificationOut])
def notifications(
    unread: bool = False, db: Session = Depends(get_db), officer: Officer = Depends(current_officer)
) -> list[schemas.NotificationOut]:
    q = (
        select(Notification)
        .where((Notification.officer_id == officer.id) | (Notification.officer_id.is_(None)))
        .order_by(Notification.created_at.desc())
        .limit(100)
    )
    if unread:
        q = q.where(Notification.read_at.is_(None))
    return [
        schemas.NotificationOut(
            id=n.id,
            kind=n.kind,
            title=n.title,
            body=n.body,
            change_id=n.change_id,
            created_at=n.created_at,
            read_at=n.read_at,
        )
        for n in db.scalars(q)
    ]


@router.post("/notifications/{notification_id}/read", status_code=204, response_model=None)
def mark_read(
    notification_id: uuid.UUID,
    db: Session = Depends(get_db),
    officer: Officer = Depends(current_officer),
) -> None:
    from sqlalchemy import func

    n = db.get(Notification, notification_id)
    if n is None:
        raise HTTPException(404, "notification not found")
    n.read_at = func.now()
