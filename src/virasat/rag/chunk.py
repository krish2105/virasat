"""Clause-aware chunking of the JHCPR 2020 corpus. Never fixed-size.

The PDF has two parts with independent numbering: the Regulations (clauses
1-26, sub-clauses like 4.1 and items like (i)/(a)) and the Architectural Control
Guidelines annexure (sections 1-11 with 3.1-style subsections). Each chunk is one
clause or sub-clause with its full ancestor path in the metadata.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

import fitz

CORPUS = Path("data/raw/corpus/JHCPR_2020.pdf")
OUT = Path("data/corpus/clauses.jsonl")
REG = "Jaipur (Walled City) Heritage Conservation and Protection Regulations 2020"
PARTS = {
    "REG": "Regulations",
    "GEN": "General Guidelines for development / redevelopment",
    "ACG": "Architectural Control Guidelines (Chowkri Modikhana)",
}
ANNEX_MARKER = "Introduction to Chowkri Modikhana"

TOP = re.compile(r"^(\d{1,2})\.\s+(?=[A-Z])")
SUB = re.compile(r"^(\d{1,2})\.(\d{1,2})\.?\s+")
ITEM = re.compile(r"^\(?(?:[ivx]{1,4}|[a-z]|\d{1,2}\.?)\)\s+")
TERM = re.compile(r"^([A-Z][A-Za-z /\-]{2,40}):\s")
GEN_MARKER = "General Guidelines for development"
MIN_ITEM_CHARS = 150
ZONES = ["core", "buffer"]
TYPES = ["NEW_CONSTRUCTION", "VERTICAL_ADDITION", "DEMOLITION", "FACADE_ALTERATION"]
TYPE_KEYWORDS = {
    "NEW_CONSTRUCTION": (
        r"new construction|new building|construct|setback|ground coverage|built.?up"
    ),
    "VERTICAL_ADDITION": r"height|floor|storey|stories|parapet|terrace|vertical",
    "DEMOLITION": r"demoli|dismantl|removal of|pull down",
    "FACADE_ALTERATION": (
        r"fa[cç]ade|elevation|colour|color|material|signage|jharokha|door|window"
        r"|balcon|railing|plaster|paint"
    ),
}


@dataclass
class Chunk:
    clause_id: str
    regulation: str
    part: str
    section: str
    clause: str
    path: str
    text: str
    source_page: int
    source_doc_sha256: str
    applies_to_zone: list[str] = field(default_factory=lambda: list(ZONES))
    applies_to_change_type: list[str] = field(default_factory=list)


def _lines(doc: fitz.Document) -> list[tuple[int, str]]:
    out = []
    for i, page in enumerate(doc, start=1):
        for ln in page.get_text().splitlines():
            s = ln.replace("\x00", "").strip()
            if s and not re.fullmatch(r"\d{1,3}", s):  # drop bare page numbers
                out.append((i, s))
    return out


def _change_types(text: str) -> list[str]:
    hits = [t for t, pat in TYPE_KEYWORDS.items() if re.search(pat, text, re.I)]
    return hits or list(TYPES)  # a clause with no signal applies to all types


def _chars(buf: list[str]) -> int:
    return len(" ".join(buf))


def _child(parent: Chunk, label: str, page: int, sha: str) -> Chunk:
    sep = "" if label.startswith("(") else " "
    return Chunk(
        f"{parent.clause_id}{sep}{label}",
        REG,
        parent.part,
        parent.section,
        f"{parent.clause}{sep}{label}",
        f"{parent.path} > {label}",
        "",
        page,
        sha,
    )


def parse(doc: fitz.Document, sha: str) -> list[Chunk]:
    chunks: list[Chunk] = []
    part, top_n, top_title, sub_id, sub_title = "REG", 0, "", "", ""
    buf: list[str] = []
    cur: Chunk | None = None
    parent: Chunk | None = None  # enclosing clause for enumerated items
    skip_page = 0

    def flush() -> None:
        nonlocal cur, buf
        if cur is not None and buf:
            cur.text = " ".join(buf).strip()
            cur.applies_to_change_type = _change_types(cur.text)
            chunks.append(cur)
        cur, buf = None, []

    for page, line in _lines(doc):
        if ANNEX_MARKER in line and part in ("REG", "GEN"):
            flush()
            part, top_n, top_title, sub_id, parent = "ACG", 0, "", "", None
            skip_page = page  # the annexure opens with a table of contents
            continue
        if page == skip_page:
            continue
        if line.startswith(GEN_MARKER) and part == "REG":
            flush()
            part, top_n, top_title, sub_id, parent = "GEN", 0, "", "", None
            cur = Chunk(
                f"{part}-0", REG, PARTS[part], "0", "0", f"{REG} > {PARTS[part]}", "", page, sha
            )
            parent = cur
            buf = [line]
            continue
        m_sub, m_top = SUB.match(line), TOP.match(line)
        if m_sub and int(m_sub.group(1)) == top_n:
            flush()
            sub_id = f"{m_sub.group(1)}.{m_sub.group(2)}"
            sub_title = re.split(r"[.\-–:]\s", line[m_sub.end() :], maxsplit=1)[0].strip(" .-–:")
            cur = Chunk(
                f"{part}-{sub_id}",
                REG,
                PARTS[part],
                str(top_n),
                sub_id,
                f"{REG} > {PARTS[part]} > {top_n}. {top_title} > {sub_id} {sub_title}",
                "",
                page,
                sha,
            )
            buf = [line[m_sub.end() :].strip()]
            parent = cur
        elif m_top and int(m_top.group(1)) in (top_n + 1, top_n + 2):
            flush()
            top_n = int(m_top.group(1))
            top_title = re.split(r"[.\-–:]\s", line[m_top.end() :], maxsplit=1)[0].strip(" .-–:")
            sub_id = ""
            cur = Chunk(
                f"{part}-{top_n}",
                REG,
                PARTS[part],
                str(top_n),
                str(top_n),
                f"{REG} > {PARTS[part]} > {top_n}. {top_title}",
                "",
                page,
                sha,
            )
            buf = [line[m_top.end() :].strip()]
            parent = cur
        elif (m_item := ITEM.match(line)) and parent is not None and _chars(buf) > MIN_ITEM_CHARS:
            # enumerations: each item becomes its own chunk, a sibling under the clause
            flush()
            item = m_item.group(0).strip()
            cur = _child(parent, item, page, sha)
            buf = [line]
        elif (
            (m_term := TERM.match(line))
            and parent is not None
            and "Definitions" in parent.path
            and _chars(buf) > MIN_ITEM_CHARS
        ):
            flush()
            cur = _child(parent, m_term.group(1), page, sha)
            buf = [line]
        elif cur is not None:
            buf.append(line)
    flush()
    seen: dict[str, int] = {}
    for c in chunks:  # e.g. (i) as a letter and (i) as a roman numeral in the same clause
        seen[c.clause_id] = seen.get(c.clause_id, 0) + 1
        if seen[c.clause_id] > 1:
            c.clause_id = f"{c.clause_id}-{seen[c.clause_id]}"
    return chunks


def main() -> None:
    if not CORPUS.exists():
        raise SystemExit(f"chunk: {CORPUS} missing — corpus not acquired")
    sha = hashlib.sha256(CORPUS.read_bytes()).hexdigest()
    chunks = parse(fitz.open(CORPUS), sha)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w") as f:
        for c in chunks:
            f.write(json.dumps(asdict(c), ensure_ascii=False) + "\n")
    lens = sorted(len(c.text) for c in chunks)
    print(
        f"chunk: {len(chunks)} clauses -> {OUT}; text length median {lens[len(lens)//2]}, "
        f"max {lens[-1]}; parts {dict((p, sum(c.part == PARTS[p] for c in chunks)) for p in PARTS)}"
    )


if __name__ == "__main__":
    main()
