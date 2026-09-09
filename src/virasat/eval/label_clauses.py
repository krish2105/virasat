"""`uv run label-clauses` — the owner labels (change description, applicable clause) pairs.

Each round shows the top-10 retrieved clauses for a description you type; you pick
the ones that actually govern the change (comma-separated numbers), or type a clause
id directly, or 'none'. Rows append to data/corpus/retrieval_pairs.jsonl.
"""

from __future__ import annotations

import json
import sys

from virasat.eval.retrieval import PAIRS
from virasat.rag.retrieve import hybrid_search

ZONES = ["core", "buffer"]
TYPES = ["NEW_CONSTRUCTION", "VERTICAL_ADDITION", "DEMOLITION", "FACADE_ALTERATION"]


def main() -> None:
    PAIRS.parent.mkdir(parents=True, exist_ok=True)
    print(f"labelling into {PAIRS}; Ctrl-C to stop\n")
    while True:
        try:
            query = input("change description> ").strip()
            if not query:
                continue
            zone = input(f"zone {ZONES}> ").strip() or "core"
            ctype = input(f"change type {TYPES}> ").strip() or TYPES[0]
            hits = hybrid_search(query, zone, ctype, k=10)
            for i, h in enumerate(hits, start=1):
                print(f"  [{i}] {h.clause_id:<22} {h.path[-70:]}\n       {h.text[:160]}")
            raw = input("governing clause numbers (e.g. 1,3) or clause id or 'none'> ").strip()
        except (KeyboardInterrupt, EOFError):
            print()
            sys.exit(0)
        if raw.lower() == "none":
            ids: list[str] = []
        elif raw.replace(",", "").replace(" ", "").isdigit():
            ids = [hits[int(i) - 1].clause_id for i in raw.split(",") if i.strip()]
        else:
            ids = [raw]
        with PAIRS.open("a") as f:
            f.write(
                json.dumps({"query": query, "zone": zone, "change_type": ctype, "clause_ids": ids})
                + "\n"
            )
        print(f"saved -> {ids}\n")
