import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from virasat.api import schemas
from virasat.api.deps import current_officer, get_db
from virasat.api.serialize import change_detail, change_summary
from virasat.db.models import (
    AuditLog,
    Change,
    ChangeStatus,
    Decision,
    Finding,
    Notification,
    Officer,
    OfficerDecision,
)

router = APIRouter(tags=["queue"])
PRIORITY_ORDER = {"urgent": 0, "high": 1, "normal": 2, "low": 3, "none": 4}
DECISION_STATUS = {
    "approve": ChangeStatus.approved,
    "reject": ChangeStatus.rejected,
    "escalate": ChangeStatus.escalated,
}


@router.get("/queue", response_model=schemas.QueuePage)
def queue(
    zone: str | None = None,
    status: str = "pending",
    severity: str | None = None,
    chowkri: str | None = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    db: Session = Depends(get_db),
    officer: Officer = Depends(current_officer),
) -> schemas.QueuePage:
    q = select(Change)
    if status != "all":
        statuses = [ChangeStatus(s) for s in status.split(",")]
        q = q.where(Change.status.in_(statuses))
    if zone:
        q = q.where(Change.zone == zone)
    if chowkri:
        q = q.where(Change.chowkri_id == chowkri)
    rows = list(db.scalars(q))
    findings: dict[uuid.UUID, list[Finding]] = {}
    for f in (
        db.scalars(select(Finding).where(Finding.change_id.in_([c.id for c in rows])))
        if rows
        else []
    ):
        findings.setdefault(f.change_id, []).append(f)
    items = [change_summary(c, findings.get(c.id, [])) for c in rows]
    if severity:
        items = [i for i in items if i.severity == severity]
    items.sort(
        key=lambda i: (
            PRIORITY_ORDER.get(i.priority, 9),
            -["low", "medium", "high"].index(i.severity) if i.severity else 0,
            i.created_at,
        )
    )
    return schemas.QueuePage(items=items[offset : offset + limit], total=len(items))


@router.get("/changes/{change_id}", response_model=schemas.ChangeDetail)
def change(
    change_id: uuid.UUID, db: Session = Depends(get_db), officer: Officer = Depends(current_officer)
) -> schemas.ChangeDetail:
    c = db.get(Change, change_id)
    if c is None:
        raise HTTPException(404, "change not found")
    return change_detail(db, c)


@router.post("/changes/{change_id}/decision", response_model=schemas.ChangeDetail)
def decide(
    change_id: uuid.UUID,
    body: schemas.DecisionIn,
    db: Session = Depends(get_db),
    officer: Officer = Depends(current_officer),
) -> schemas.ChangeDetail:
    c = db.get(Change, change_id)
    if c is None:
        raise HTTPException(404, "change not found")
    if c.status == ChangeStatus.dropped:
        raise HTTPException(409, "dropped changes are not in the queue")
    db.add(
        OfficerDecision(
            change_id=c.id,
            officer_id=officer.id,
            decision=Decision(body.decision),
            reason=body.reason,
        )
    )
    c.status = DECISION_STATUS[body.decision]
    db.add(
        AuditLog(
            actor=f"officer:{officer.username}",
            action=f"decision:{body.decision}",
            change_id=c.id,
            payload={"reason": body.reason, "previous_status": c.status.value},
        )
    )
    if body.decision == "escalate":
        db.add(
            Notification(
                kind="escalation",
                title="Change escalated for site visit",
                body=f"{c.change_type.value} in {c.chowkri_id or c.zone.value} escalated by "
                f"{officer.display_name}",
                change_id=c.id,
            )
        )
    db.flush()
    return change_detail(db, c)


@router.get("/queue/counts", response_model=dict[str, int])
def counts(
    db: Session = Depends(get_db), officer: Officer = Depends(current_officer)
) -> dict[str, int]:
    rows = db.execute(select(Change.status, func.count()).group_by(Change.status)).all()
    return {s.value: n for s, n in rows}
