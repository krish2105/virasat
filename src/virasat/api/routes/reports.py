"""Dossier export, fairness and health metrics, public aggregate map, audit log."""

from __future__ import annotations

import csv
import io
import json
import uuid
from datetime import date
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response, StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from virasat.api import schemas
from virasat.api.deps import current_officer, get_db
from virasat.api.routes.runs import run_out
from virasat.api.serialize import change_summary
from virasat.db.models import (
    AuditLog,
    Change,
    ChangeStatus,
    Decision,
    Finding,
    Officer,
    OfficerDecision,
    Run,
)
from virasat.eval import fairness
from virasat.eval.retrieval import evaluate as retrieval_eval

router = APIRouter(tags=["reports"])
PIPELINE_REPORT = Path("data/processed/pipeline_report.json")
TEMPERATURE = Path("data/processed/temperature.json")


def _window(db: Session, start: date | None, end: date | None) -> list[Change]:
    q = select(Change).where(Change.status != ChangeStatus.dropped)
    if start:
        q = q.where(Change.epoch_after >= start)
    if end:
        q = q.where(Change.epoch_after <= end)
    return list(db.scalars(q))


def _dossier_rows(db: Session, changes: list[Change]) -> list[dict[str, Any]]:
    findings: dict[uuid.UUID, list[Finding]] = {}
    for f in (
        db.scalars(select(Finding).where(Finding.change_id.in_([c.id for c in changes])))
        if changes
        else []
    ):
        findings.setdefault(f.change_id, []).append(f)
    rows = []
    for c in changes:
        s = change_summary(c, findings.get(c.id, []))
        rows.append(
            {
                **s.model_dump(mode="json"),
                "findings": [
                    {"claim": f.claim, "clause_id": f.clause_id, "severity": f.severity.value}
                    for f in findings.get(c.id, [])
                    if f.is_final
                ],
            }
        )
    return rows


@router.get("/dossier")
def dossier(
    start: date | None = None,
    end: date | None = None,
    db: Session = Depends(get_db),
    officer: Officer = Depends(current_officer),
) -> dict[str, object]:
    changes = _window(db, start, end)
    rows = _dossier_rows(db, changes)

    def counts(col: Any) -> dict[str, int]:
        rows = db.execute(select(col, func.count()).group_by(col)).all()
        return {str(getattr(k, "value", k)): int(n) for k, n in rows}

    agg = {
        "by_type": counts(Change.change_type),
        "by_zone": counts(Change.zone),
        "by_chowkri": counts(Change.chowkri_id),
        "by_status": counts(Change.status),
    }
    return {
        "generated": date.today().isoformat(),
        "window": [start, end],
        "count": len(rows),
        "aggregates": agg,
        "changes": rows,
        "attribution": schemas.AggregateOut(cells=[], window=None).attribution,
    }


@router.get("/dossier.csv")
def dossier_csv(
    start: date | None = None,
    end: date | None = None,
    db: Session = Depends(get_db),
    officer: Officer = Depends(current_officer),
) -> StreamingResponse:
    rows = _dossier_rows(db, _window(db, start, end))
    buf = io.StringIO()
    cols = [
        "id",
        "building_id",
        "zone",
        "chowkri_id",
        "change_type",
        "change_prob",
        "status",
        "priority",
        "severity",
        "epoch_before",
        "epoch_after",
        "findings",
    ]
    w = csv.DictWriter(buf, fieldnames=cols, extrasaction="ignore")
    w.writeheader()
    for r in rows:
        w.writerow(
            {**r, "findings": "; ".join(f"{f['clause_id']}: {f['claim']}" for f in r["findings"])}
        )
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=virasat-dossier.csv"},
    )


@router.get("/dossier.pdf")
def dossier_pdf(
    start: date | None = None,
    end: date | None = None,
    db: Session = Depends(get_db),
    officer: Officer = Depends(current_officer),
) -> Response:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table

    rows = _dossier_rows(db, _window(db, start, end))
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, title="VIRASAT dossier")
    st = getSampleStyleSheet()
    story = [
        Paragraph("VIRASAT — Heritage Impact Assessment dossier", st["Title"]),
        Paragraph(
            f"Window: {start or 'start'} to {end or date.today()} · {len(rows)} changes · "
            f"generated {date.today()} · every finding below is a recommendation "
            "reviewed by a named officer",
            st["Normal"],
        ),
        Spacer(1, 12),
    ]
    data = [["Change", "Chowkri", "Type", "Status", "Severity", "Findings"]]
    for r in rows:
        data.append(
            [
                str(r["id"])[:8],
                r["chowkri_id"] or r["zone"],
                r["change_type"],
                r["status"],
                r["severity"] or "-",
                "\n".join(f"{f['clause_id']}: {f['claim']}" for f in r["findings"])[:400],
            ]
        )
    story.append(Table(data, colWidths=[50, 70, 90, 60, 50, 200], repeatRows=1))
    story.append(Spacer(1, 12))
    story.append(Paragraph(schemas.AggregateOut(cells=[], window=None).attribution, st["Normal"]))
    doc.build(story)
    return Response(
        buf.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=virasat-dossier.pdf"},
    )


@router.get("/metrics/fairness", response_model=schemas.FairnessOut)
def fairness_metrics(
    db: Session = Depends(get_db), officer: Officer = Depends(current_officer)
) -> schemas.FairnessOut:
    return schemas.FairnessOut(**fairness.report(db))


@router.get("/metrics/health", response_model=schemas.HealthMetrics)
def health_metrics(
    db: Session = Depends(get_db), officer: Officer = Depends(current_officer)
) -> schemas.HealthMetrics:
    queue = {
        s.value: n
        for s, n in db.execute(select(Change.status, func.count()).group_by(Change.status)).all()
    }
    decided = db.execute(
        select(OfficerDecision.decision, func.count()).group_by(OfficerDecision.decision)
    ).all()
    total = sum(n for _, n in decided)
    agreement = (sum(n for d, n in decided if d == Decision.approve) / total) if total else None
    return schemas.HealthMetrics(
        pipeline=json.loads(PIPELINE_REPORT.read_text()) if PIPELINE_REPORT.exists() else None,
        calibration=json.loads(TEMPERATURE.read_text()) if TEMPERATURE.exists() else None,
        retrieval=retrieval_eval()
        if False
        else {"status": "BLOCKED", "reason": "computed by `uv run eval`"},
        fairness=schemas.FairnessOut(**fairness.report(db)),
        queue=queue,
        runs=[
            run_out(r) for r in db.scalars(select(Run).order_by(Run.started_at.desc()).limit(10))
        ],
        agreement_rate=agreement,
    )


@router.get("/map/aggregate", response_model=schemas.AggregateOut)
def map_aggregate(
    start: date | None = None, end: date | None = None, db: Session = Depends(get_db)
) -> schemas.AggregateOut:
    """Public. Counts per chowkri only — nothing here can identify a property."""
    q = select(
        Change.chowkri_id, Change.zone, Change.change_type, Change.status, func.count()
    ).where(Change.status != ChangeStatus.dropped, Change.chowkri_id.is_not(None))
    if start:
        q = q.where(Change.epoch_after >= start)
    if end:
        q = q.where(Change.epoch_after <= end)
    cells: dict[str, schemas.AggregateCell] = {}
    for chowkri, zone, ctype, status, n in db.execute(
        q.group_by(Change.chowkri_id, Change.zone, Change.change_type, Change.status)
    ).all():
        cell = cells.setdefault(
            chowkri,
            schemas.AggregateCell(
                chowkri_id=chowkri, zone=zone.value, counts_by_type={}, counts_by_status={}
            ),
        )
        cell.counts_by_type[ctype.value] = cell.counts_by_type.get(ctype.value, 0) + n
        cell.counts_by_status[status.value] = cell.counts_by_status.get(status.value, 0) + n
    return schemas.AggregateOut(
        cells=list(cells.values()), window=(start, end) if start and end else None
    )


@router.get("/audit", response_model=list[schemas.AuditRow])
def audit(
    change_id: uuid.UUID | None = None,
    limit: int = Query(200, le=1000),
    offset: int = 0,
    db: Session = Depends(get_db),
    officer: Officer = Depends(current_officer),
) -> list[schemas.AuditRow]:
    q = select(AuditLog).order_by(AuditLog.ts.desc()).offset(offset).limit(limit)
    if change_id:
        q = q.where(AuditLog.change_id == change_id)
    return [
        schemas.AuditRow(
            id=r.id,
            ts=r.ts,
            actor=r.actor,
            action=r.action,
            change_id=r.change_id,
            payload=dict(r.payload),
            git_sha=r.git_sha,
            model_ids=dict(r.model_ids),
            prompt_versions=dict(r.prompt_versions),
            total_tokens=r.total_tokens,
        )
        for r in db.scalars(q)
    ]
