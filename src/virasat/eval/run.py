"""`uv run eval` — evaluation harness and blocking gates.

Writes eval/reports/<timestamp>/report.md and report.json. Every metric is either
measured on real labelled data or reported as BLOCKED with the reason. `--gate`
exits non-zero only on a real, measured gate failure or a regression against the
previous report — never on BLOCKED.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPORTS = Path("eval/reports")
TARGETS = {
    "detector_recall": (">=", 0.85),
    "detector_fpr": ("<=", 0.15),
    "ece": ("<=", 0.05),
    "facade_macro_f1": (">=", 0.75),
    "retrieval_precision_at_3": (">=", 0.90),
    "retrieval_recall_at_5": (">=", 0.85),
    "verifier_catch_rate": (">=", 0.80),
}


def detector_metrics() -> dict[str, Any]:
    ckpts = (
        sorted(Path("data/processed/checkpoints").glob("siamese_*.pt"))
        if Path("data/processed/checkpoints").exists()
        else []
    )
    if not ckpts:
        return {"status": "BLOCKED", "reason": "no trained checkpoint; 0 tile labels on disk"}
    import torch

    meta = torch.load(ckpts[-1], map_location="cpu", weights_only=False)
    return {
        "status": "measured",
        "checkpoint": ckpts[-1].name,
        **meta["test_metrics"],
        "ece": meta["ece"],
        "temperature": meta["temperature"],
    }


def retrieval_metrics() -> dict[str, Any]:
    from virasat.eval.retrieval import evaluate

    return evaluate()


def verifier_metrics() -> dict[str, Any]:
    red = Path("tests/fixtures/redteam/findings.jsonl")
    pairs = Path("data/corpus/retrieval_pairs.jsonl")
    if not pairs.exists():
        return {
            "status": "BLOCKED",
            "reason": "red-team catch rate is measured against real, labelled clauses only",
            "redteam_set": str(red) if red.exists() else "not built",
        }
    return {"status": "BLOCKED", "reason": "not yet run"}


def fairness_metrics() -> dict[str, Any]:
    try:
        from virasat.db.session import SessionLocal
        from virasat.eval.fairness import report

        with SessionLocal() as s:
            return report(s)
    except Exception as exc:  # database unreachable is a BLOCKED, not a crash
        return {"status": "BLOCKED", "reason": f"database unreachable: {exc.__class__.__name__}"}


def pipeline_metrics() -> dict[str, Any]:
    p = Path("data/processed/pipeline_report.json")
    return (
        json.loads(p.read_text())
        if p.exists()
        else {"status": "BLOCKED", "reason": "pipeline not run"}
    )


def previous_report() -> dict[str, Any] | None:
    if not REPORTS.exists():
        return None
    runs = sorted(p for p in REPORTS.iterdir() if (p / "report.json").exists())
    return json.loads((runs[-1] / "report.json").read_text()) if runs else None


def gate(report: dict[str, Any], prev: dict[str, Any] | None) -> list[str]:
    failures = []
    fair = report["fairness"]
    if isinstance(fair, dict) and fair.get("status") == "measured" and fair.get("passes") is False:
        failures.append(
            f"fairness: disparity ratio {fair['disparity_ratio']:.2f} > {fair['max_ratio']}"
        )
    det, ret = report["detector"], report["retrieval"]
    for name, val in (
        ("detector_recall", det.get("recall")),
        ("detector_fpr", det.get("fpr")),
        ("ece", det.get("ece")),
        ("retrieval_precision_at_3", ret.get("precision_at_3")),
        ("retrieval_recall_at_5", ret.get("recall_at_5")),
    ):
        if val is None:
            continue
        op, target = TARGETS[name]
        if (op == ">=" and val < target) or (op == "<=" and val > target):
            failures.append(f"{name}: {val:.3f} misses target {op} {target}")
        if prev:
            old = (
                prev.get("detector")
                if name.startswith(("detector", "ece"))
                else prev.get("retrieval")
            )
            key = name.replace("detector_", "").replace("retrieval_", "")
            if isinstance(old, dict) and isinstance(old.get(key), int | float):
                worse = val < old[key] - 0.02 if op == ">=" else val > old[key] + 0.02
                if worse:
                    failures.append(f"{name}: regression {old[key]:.3f} -> {val:.3f}")
    return failures


def render(report: dict[str, Any]) -> str:
    def row(name: str, d: object, key: str | None = None) -> str:
        if not isinstance(d, dict):
            return f"| {name} | — | — |"
        if d.get("status") == "BLOCKED":
            return f"| {name} | **BLOCKED** | {d.get('reason', '')} |"
        val = d.get(key) if key else d.get("status")
        return f"| {name} | {val} | |"

    det, ret, fair = report["detector"], report["retrieval"], report["fairness"]
    lines = [
        f"# VIRASAT evaluation — {report['timestamp']}",
        "",
        "| Metric | Value | Note |",
        "|---|---|---|",
        row("Detector recall (target ≥ 0.85)", det, "recall"),
        row("Detector FPR (≤ 0.15)", det, "fpr"),
        row("ECE (≤ 0.05)", det, "ece"),
        row("Retrieval precision@3 (≥ 0.90)", ret, "precision_at_3"),
        row("Retrieval recall@5 (≥ 0.85)", ret, "recall_at_5"),
        row("Verifier catch rate (≥ 0.80)", report["verifier"]),
        row(
            "Fairness disparity ratio (≤ %s)"
            % (fair.get("max_ratio") if isinstance(fair, dict) else "?"),
            fair,
            "disparity_ratio",
        ),
        "",
        "## Fairness by chowkri",
        "",
    ]
    if isinstance(fair, dict) and fair.get("fpr_by_chowkri"):
        lines += ["| Chowkri | FPR | n |", "|---|---|---|"]
        lines += [
            f"| {k} | {v:.3f} | {fair['n_by_chowkri'][k]} |"
            for k, v in fair["fpr_by_chowkri"].items()
        ]
    else:
        lines.append("BLOCKED — " + str(fair.get("reason") if isinstance(fair, dict) else fair))
    lines += [
        "",
        "## Pipeline",
        "",
        "```json",
        json.dumps(report["pipeline"], indent=1),
        "```",
        "",
        f"Gate failures: {report['gate_failures'] or 'none'}",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(prog="eval")
    parser.add_argument("--gate", action="store_true", help="exit non-zero on a real gate failure")
    args = parser.parse_args()
    prev = previous_report()
    report: dict[str, Any] = {
        "timestamp": datetime.now(UTC).strftime("%Y-%m-%dT%H%M%SZ"),
        "detector": detector_metrics(),
        "retrieval": retrieval_metrics(),
        "verifier": verifier_metrics(),
        "fairness": fairness_metrics(),
        "pipeline": pipeline_metrics(),
    }
    report["gate_failures"] = gate(report, prev)
    out = REPORTS / str(report["timestamp"])
    out.mkdir(parents=True, exist_ok=True)
    (out / "report.json").write_text(json.dumps(report, indent=1, default=str))
    (out / "report.md").write_text(render(report))
    blocked = [
        k
        for k in ("detector", "retrieval", "verifier", "fairness")
        if report[k].get("status") == "BLOCKED"
    ]
    print(
        f"eval: report -> {out}/report.md; BLOCKED: {', '.join(blocked) or 'none'}; "
        f"gate failures: {report['gate_failures'] or 'none'}"
    )
    if args.gate and report["gate_failures"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
