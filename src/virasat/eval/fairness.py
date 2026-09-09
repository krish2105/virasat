"""Per-chowkri false-positive-rate disparity. A blocking gate, not a dashboard number."""

from __future__ import annotations

from pathlib import Path

import yaml
from sqlalchemy import select
from sqlalchemy.orm import Session

from virasat.db.models import Change, ChangeStatus, Decision, OfficerDecision

CONFIG = Path("config/fairness.yaml")


def config() -> dict[str, float]:
    cfg: dict[str, float] = yaml.safe_load(CONFIG.read_text())
    return cfg


def fairness_gate(fpr_by_chowkri: dict[str, float], max_ratio: float) -> bool:
    """FPR disparity ratio across wards. Returns False to FAIL the build.

    A model that flags one neighbourhood at three times the false rate of
    another is not a heritage tool, it is a discrimination engine.
    """
    vals = [v for v in fpr_by_chowkri.values() if v > 0]
    if len(vals) < 2:
        return True  # not enough wards to compare
    return (max(vals) / min(vals)) <= max_ratio


def fpr_from_decisions(db: Session) -> tuple[dict[str, float], dict[str, int]]:
    """Officer rejections are the strongest false-positive label once the queue is live."""
    decided = db.execute(
        select(Change.chowkri_id, OfficerDecision.decision)
        .join(OfficerDecision, OfficerDecision.change_id == Change.id)
        .where(
            Change.zone == "core",
            Change.chowkri_id.is_not(None),
            Change.status.in_(
                [ChangeStatus.approved, ChangeStatus.rejected, ChangeStatus.escalated]
            ),
        )
    ).all()
    n: dict[str, int] = {}
    fp: dict[str, int] = {}
    for chowkri, decision in decided:
        n[chowkri] = n.get(chowkri, 0) + 1
        if decision == Decision.reject:
            fp[chowkri] = fp.get(chowkri, 0) + 1
    return {k: fp.get(k, 0) / v for k, v in n.items()}, n


def report(db: Session) -> dict[str, object]:
    cfg = config()
    fpr, n = fpr_from_decisions(db)
    enough = {k: v for k, v in fpr.items() if n[k] >= cfg["min_labelled_per_chowkri"]}
    if len(enough) < 2:
        return {
            "status": "BLOCKED",
            "max_ratio": cfg["max_ratio"],
            "fpr_by_chowkri": fpr,
            "n_by_chowkri": n,
            "reason": (
                f"need >= {int(cfg['min_labelled_per_chowkri'])} officer decisions in at "
                f"least two chowkris; have {len(enough)}"
            ),
        }
    vals = [v for v in enough.values() if v > 0]
    ratio = (max(vals) / min(vals)) if len(vals) >= 2 else None
    return {
        "status": "measured",
        "max_ratio": cfg["max_ratio"],
        "fpr_by_chowkri": enough,
        "n_by_chowkri": n,
        "disparity_ratio": ratio,
        "passes": fairness_gate(enough, cfg["max_ratio"]),
    }
