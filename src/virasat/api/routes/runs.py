import subprocess
import time
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from virasat.api import schemas
from virasat.api.deps import get_db, require_role
from virasat.db.models import AuditLog, Officer, Role, Run

router = APIRouter(prefix="/runs", tags=["runs"])
_last_start = 0.0
RATE_LIMIT_S = 300.0  # a batch run is expensive


def run_out(r: Run) -> schemas.RunOut:
    return schemas.RunOut(
        id=r.id,
        status=r.status,
        started_at=r.started_at,
        finished_at=r.finished_at,
        epoch_before=r.epoch_before,
        epoch_after=r.epoch_after,
        git_sha=r.git_sha,
        total_tokens=r.total_tokens,
        progress=dict(r.progress),
    )


@router.post("", response_model=schemas.RunOut, status_code=202)
def start_run(
    body: schemas.RunIn,
    db: Session = Depends(get_db),
    officer: Officer = Depends(require_role(Role.admin, Role.reviewer)),
) -> schemas.RunOut:
    global _last_start
    now = time.monotonic()
    if now - _last_start < RATE_LIMIT_S:
        raise HTTPException(
            429, f"a run was started {int(now - _last_start)}s ago; wait {int(RATE_LIMIT_S)}s"
        )
    _last_start = now
    try:
        sha = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        sha = "unknown"
    run = Run(
        epoch_before=body.epoch_before,
        epoch_after=body.epoch_after,
        git_sha=sha,
        config_hash="api",
        status="queued",
        progress={
            "note": "batch detection runs on the inference host: `uv run pipeline && uv run agents`"
        },
    )
    db.add(run)
    db.add(
        AuditLog(
            actor=f"officer:{officer.username}",
            action="run:queued",
            payload=body.model_dump(mode="json"),
        )
    )
    db.flush()
    return run_out(run)


@router.get("", response_model=list[schemas.RunOut])
def list_runs(
    db: Session = Depends(get_db), officer: Officer = Depends(require_role(*Role))
) -> list[schemas.RunOut]:
    return [run_out(r) for r in db.scalars(select(Run).order_by(Run.started_at.desc()).limit(20))]


@router.get("/{run_id}", response_model=schemas.RunOut)
def get_run(
    run_id: uuid.UUID,
    db: Session = Depends(get_db),
    officer: Officer = Depends(require_role(*Role)),
) -> schemas.RunOut:
    r = db.get(Run, run_id)
    if r is None:
        raise HTTPException(404, "run not found")
    return run_out(r)
