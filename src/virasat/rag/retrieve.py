"""Hybrid clause retrieval: metadata pre-filter -> BM25 + dense -> RRF -> cross-encoder.

The pre-filter is a SQL WHERE on zone and change type, applied before any vector
search: a facade-colour clause is never a candidate for a demolition finding.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml
from rank_bm25 import BM25Okapi
from sentence_transformers import CrossEncoder
from sqlalchemy import select

from virasat.db.models import Clause
from virasat.db.session import session_scope
from virasat.rag.embed import embed_query

TOP_DENSE = 20
TOP_BM25 = 20
RERANK_POOL = 20


@dataclass(frozen=True)
class RetrievedClause:
    clause_id: str
    path: str
    text: str
    score: float
    source_page: int


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


@lru_cache(maxsize=1)
def _reranker() -> CrossEncoder:
    cfg = yaml.safe_load(Path("config/models.yaml").read_text())["reranker"]
    return CrossEncoder(cfg["model"])


def hybrid_search(query: str, zone: str, change_type: str, k: int = 5) -> list[RetrievedClause]:
    with session_scope() as s:
        filt = (
            Clause.applies_to_zone.any(zone),  # type: ignore[arg-type]
            Clause.applies_to_change_type.any(change_type),  # type: ignore[arg-type]
        )
        candidates = list(s.scalars(select(Clause).where(*filt)))
        if not candidates:
            return []
        dense_ids = list(
            s.scalars(
                select(Clause.id)
                .where(*filt)
                .order_by(Clause.embedding.cosine_distance(embed_query(query)))
                .limit(TOP_DENSE)
            )
        )
    by_id = {c.id: c for c in candidates}
    bm25 = BM25Okapi([_tokens(f"{c.path} {c.text}") for c in candidates])
    scores = bm25.get_scores(_tokens(query))
    bm25_ids = [
        candidates[i].id
        for i in sorted(range(len(candidates)), key=lambda i: -scores[i])[:TOP_BM25]
    ]

    fused: dict[str, float] = {}
    for ranking in (dense_ids, bm25_ids):
        for rank, cid in enumerate(ranking):
            fused[cid] = fused.get(cid, 0.0) + 1.0 / (60 + rank)  # reciprocal-rank fusion
    pool = sorted(fused, key=fused.get, reverse=True)[:RERANK_POOL]  # type: ignore[arg-type]

    pairs = [(query, f"{by_id[cid].path}\n{by_id[cid].text}") for cid in pool]
    rerank = _reranker().predict(pairs)
    order = sorted(range(len(pool)), key=lambda i: -float(rerank[i]))[:k]
    return [
        RetrievedClause(
            pool[i],
            by_id[pool[i]].path,
            by_id[pool[i]].text,
            float(rerank[i]),
            by_id[pool[i]].source_page,
        )
        for i in order
    ]
