"""Retrieval evaluation on owner-labelled (change description, clause) pairs.

Reports precision@3 and recall@5 only when at least MIN_PAIRS labelled rows exist;
otherwise the status is BLOCKED. Never computed on synthetic pairs.
"""

from __future__ import annotations

import json
from pathlib import Path

PAIRS = Path("data/corpus/retrieval_pairs.jsonl")
MIN_PAIRS = 60
TARGET_P3 = 0.90


def load_pairs() -> list[dict[str, object]]:
    if not PAIRS.exists():
        return []
    return [json.loads(ln) for ln in PAIRS.read_text().splitlines() if ln.strip()]


def evaluate() -> dict[str, object]:
    pairs = load_pairs()
    if len(pairs) < MIN_PAIRS:
        return {"status": "BLOCKED", "reason": f"{len(pairs)}/{MIN_PAIRS} labelled pairs"}
    from virasat.rag.retrieve import hybrid_search

    p3_hits = r5_hits = 0.0
    for p in pairs:
        got = [
            r.clause_id
            for r in hybrid_search(str(p["query"]), str(p["zone"]), str(p["change_type"]), k=5)
        ]
        relevant = {str(c) for c in list(p["clause_ids"])}  # type: ignore[call-overload]
        p3_hits += len(relevant & set(got[:3])) / 3
        r5_hits += len(relevant & set(got[:5])) / max(1, len(relevant))
    n = len(pairs)
    p3, r5 = p3_hits / n, r5_hits / n
    return {
        "status": "measured",
        "n": n,
        "precision_at_3": round(p3, 3),
        "recall_at_5": round(r5, 3),
        "meets_target": p3 >= TARGET_P3,
    }


if __name__ == "__main__":
    print(json.dumps(evaluate(), indent=1))
