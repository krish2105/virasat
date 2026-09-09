"""Load the citable clauses of data/corpus/clauses.jsonl into `clauses` with embeddings.

The definitions sections (Regulations 3, ACG 11) are parsed and kept in the corpus file
as part of the honest record, but they are not loaded here: a glossary entry defines a
term, it is not a provision a building can breach, so it must never be offered to the
assessor as a citable clause."""

from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import delete

from virasat.db.models import Clause
from virasat.db.session import session_scope
from virasat.rag.embed import embed_texts

CLAUSES = Path("data/corpus/clauses.jsonl")


def citable(row: dict[str, object]) -> bool:
    return "Definitions" not in str(row["path"])


def main() -> None:
    if not CLAUSES.exists():
        raise SystemExit("index: run virasat.rag.chunk first")
    parsed = [json.loads(line) for line in CLAUSES.read_text().splitlines()]
    rows = [r for r in parsed if citable(r)]
    texts = [f"{r['path']}\n{r['text']}" for r in rows]
    vectors = []
    for i in range(0, len(texts), 32):
        vectors += embed_texts(texts[i : i + 32])
    with session_scope() as s:
        s.execute(delete(Clause))
        for r, v in zip(rows, vectors, strict=True):
            s.add(
                Clause(
                    id=r["clause_id"],
                    regulation=r["regulation"],
                    section=r["section"],
                    clause=r["clause"],
                    path=r["path"],
                    text=r["text"],
                    applies_to_zone=r["applies_to_zone"],
                    applies_to_change_type=r["applies_to_change_type"],
                    source_page=r["source_page"],
                    source_doc_sha256=r["source_doc_sha256"],
                    embedding=v,
                )
            )
    print(
        f"index: upserted {len(rows)} citable clauses with {len(vectors[0])}-d embeddings "
        f"({len(parsed) - len(rows)} definitions chunks parsed but not indexed)"
    )


if __name__ == "__main__":
    main()
