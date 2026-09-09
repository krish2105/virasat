# VIRASAT — Architecture

Living document. Updated at the end of every build step. Numbers here are measured
on the data actually on disk; anything not yet measurable says **BLOCKED** with the
reason.

## Build mode

On 2026-09-09 the owner chose to build all phases in one continuous build (the
one-phase-per-session rule in `CLAUDE.md` is superseded). Phase Definitions of Done
from `MASTER-PROMPT.md` §18 remain as checkpoints. Hard rules are unchanged: no
autonomous enforcement, evidence + clause citation on every finding, no fabricated
data, blocking fairness gate, no personal data, verifier on a different model.

## Spec amendments (with the evidence that forced them)

| # | MASTER-PROMPT said | Built instead | Why |
|---|---|---|---|
| 1 | 256×256 px tiles (§8.3) | Tiles by ground extent: `tile_size_m: 320`, overlap 32 m (`config/zones.yaml`) | At Sentinel-2's 10 m a 256 px tile is 2.5 km — bigger than the 710 ha core. 320 m gives 32 px at 10 m and 80 px at Open Buildings' 4 m. |
| 2 | Bhoonidhi LISS-4 as primary imagery | Sentinel-2 L2A (Earth Search, no registration) for block-scale change **and** Google Open Buildings 2.5D Temporal (4 m, annual presence + height, 2016–2023) for building-scale signal | No NRSC account yet. Open Buildings is CC BY 4.0 / ODbL and covers Jaipur at 100 %. |
| 3 | No street-level source listed (§7) | Mapillary (CC BY-SA), `ingest/street.py`, faces/plates blurred in memory before write | Google Street View licence forbids ML use. **BLOCKED on a Mapillary token.** |
| 4 | "Heritage Regulation 2022" corpus | Jaipur (Walled City) Heritage Conservation and Protection Regulations **2020**, official LSG Rajasthan PDF, 85 pp, machine-readable | The 2022 document is not findable online on 2026-09-09; the 2020 regulation is the notified instrument and includes the Architectural Control Guidelines annexure. |
| 5 | Supabase CLI for local Postgres (§5) | Plain `docker-compose.yml`; `postgis/postgis:16-3.4` + `postgresql-16-pgvector` | Matches the literal DoD (`docker compose up`). Host port is **5434** (5432/5433 taken by native Postgres on the dev Mac). |
| 6 | `claude-sonnet-4-6` cloud model | `claude-sonnet-5` (assess) / `claude-opus-5` (verify) | Not a real model id. |
| 7 | `config/settings.py` | `src/virasat/settings.py` | Keeps settings importable as a package module; `config/` holds YAML only. |
| 8 | `dropped` table (§11.3) | `changes.status = 'dropped'` | One table, one status column; the audit log still records the drop. |
| 9 | Deploy backend on Render | Render hosts the API only; batch pipeline + Ollama agent graph run on the owner's machine against `DATABASE_URL` | Render cannot host a 14B model; local-first (§2.6) preserved. |
| 10 | `@react-three/fiber 8.17` + `drei 9.114` with React 19 | fiber 9.x + drei 10.x | R3F 8 targets React 18's reconciler; the pinned pair cannot coexist with React 19. |
| 11 | `retrieve → assess` unconditional edge (§11.4) | conditional: zero clauses → `route` | Implements §11.3's own rule ("do not fall through with an empty context"). |
| 12 | Officer id as free text on the decision endpoint | Self-hosted JWT sessions, argon2 hashes, roles officer/reviewer/admin | Owner-approved feature; an audit trail needs an identity. |

## Data on disk (all rows in `data/MANIFEST.md`)

| Source | Files | Notes |
|---|---|---|
| Sentinel-2 L2A, MGRS 43REK | 2019-12-26 (0.04 % cloud), 2025-12-04 (0.001 %) — B02/B03/B04/B08 windowed to the study bbox | Same season; EPSG:32643 native |
| Google Open Buildings 2.5D Temporal v1 | 8 annual mosaics 2016–2023 at 4 m, 3 bands | Read from COG overviews; 100 % coverage |
| OpenStreetMap | 8,747 highway/wall/gate elements; 7,579 building elements (4 bbox quadrants) | ODbL — attribution in UI footer |
| UNESCO WHC document 176277 | Vector PDF map of the inscribed property | Georeferenced, see below |
| JHCPR 2020 | Official regulation PDF | RAG corpus |

**Not acquired (owner tasks):** Bhoonidhi LISS-4 (registration), Mapillary token, the
2022 regulation text if it exists, 400 tile labels, 60 clause labels.

## Boundaries

`ingest/whc_boundary.py` extracts the red (property) and blue (buffer) vector paths
from the official map, seeds an affine transform on 13 named landmarks, then refines it
by iterative closest point between 105k map road vertices and 250k densified OSM road
vertices: **95 % matched, RMS 15.6 m, median 10.7 m**. Forcing the nominal 1:10,000
scale makes the fit worse (RMS 15.98 m), so the fitted scale (3.415 m/pt, slightly
anisotropic) is kept. Resulting areas: core **643 ha**, buffer **1,994 ha** — both
~9.5 % below the inscribed 710 / 2,205 ha. The discrepancy is recorded, not hidden
(`data/boundaries/georeference_report.json`). Ten landmark zone checks pass
(`tests/unit/test_zoning.py`).

`ingest/chowkris.py` cuts the core along PCA lines through the OSM bazaar streets
(Chandpole–Tripolia–Ramganj axis; Kishanpole, Chaura Rasta, Johari, Ghat Darwaja south;
Gangauri, Amer Road/Sireh Deori and Moti Katla north). Nine blocks, 34–168 ha. **The
name→block mapping follows the published grid description and must be verified with
the JNN Heritage Cell.**

## Pipeline (`uv run pipeline`)

reproject-check → global phase-correlation shift (−0.05, −0.15 px) → 320 m tiles →
per-tile residual → quarantine > 1.5 px → spatial split by chowkri / buffer sector
(`config/splits.yaml`) → per-band stats on the train split only → paired `.npz`.
Current run: **780 tiles**, quarantine rate **0.4 %**, residual median 0.1 px / p95 0.2 px,
core 75 / buffer 155 / outside 550; train 431 / val 214 / test 135.

## Corpus (`python -m virasat.rag.chunk`)

Clause-aware parser → **178 chunks** (Regulations 122, General Guidelines 3,
Architectural Control Guidelines 53), each with ancestor path, page, document SHA-256,
`applies_to_zone`, `applies_to_change_type` (keyword-derived — a labelling pass should
refine it). Four chunks remain long (definitions list and the new-construction section).

## Database

SQLAlchemy 2 models (`db/models.py`), Alembic migration `b1fd1e47ebc2`. `audit_log`
has BEFORE UPDATE/DELETE/TRUNCATE triggers that raise — proven by test.

## Retrieval (`rag/`)

bge-m3 (Ollama, 1024-d) embeddings in pgvector with an HNSW index (m=16,
ef_construction=64). `hybrid_search`: SQL pre-filter on `applies_to_zone` and
`applies_to_change_type` → BM25 (rank-bm25) and dense top-20 → reciprocal-rank
fusion → `BAAI/bge-reranker-base` cross-encoder → top 5. Smoke check on the real
corpus: "a historic building has been demolished" → ACG-8 *Demolition* at 0.95.
Precision@3 is **BLOCKED** until the owner labels 60 pairs (`uv run label-clauses`).

## Agents (`agents/`)

State per §11.1. `triage` is pure Python; `retrieve` has no LLM; `assess`
(qwen2.5:14b local / claude-sonnet-5 cloud, T=0.1) returns pydantic-validated JSON
with one retry; `verify` (llama3.1:8b / claude-opus-5, T=0) runs mechanical checks
(unretrieved clause, missing evidence, enforcement language) before the model;
`route` writes status, findings and an audit row carrying git SHA, model ids,
prompt versions and token count. Revision cap 2; two failures →
`needs_human_rewrite`. Postgres checkpointer via `langgraph-checkpoint-postgres`.
Nine tests on a scripted fake model cover the loop cap, drop/escalate bypass and
the corpus-gap route.

## Vision (`vision/`)

Siamese ResNet-50 (shared branches, |Δ| head, focal loss), ViT-S facade classifier,
flip/rot90/jitter augmentation only, temperature scaling + ECE. `train.py` refuses
to run below 100 tile labels. `open_buildings.py` derives building-scale candidates
from presence/height deltas (103 for 2016→2023); `infer.py` materialises them as
`changes` rows with evidence crops. Detector metrics are **BLOCKED**.

## API (`api/`) and frontend (`web/`)

All §12 endpoints plus `/auth/*`, `/audit`, `/buildings/{id}/timeline`, `/visits`,
`/notifications`, `/dossier.csv|.pdf`, `/metrics/health`. Reject requires a reason
(422 otherwise); `/map/aggregate` is public and returns per-chowkri counts only
(test asserts no property fields leak). Next 15 App Router, Tailwind 3.4 with the
§13.2 tokens and a dark palette, `next-themes`, `next-intl` (en/hi), Fraunces +
IBM Plex Sans/Devanagari + IBM Plex Mono. Landing: `InstancedMesh` massing of 2,724
footprints with Open Buildings heights, Lenis + `motion/react` scroll → year,
demolitions become wireframe ghosts, WebGL-loss and `?nogl` fall back to an
isometric SVG, reduced motion gets a slider. Officer queue is keyboard-first
(J/K/Enter/A/R/E). Five Playwright flows pass on desktop.

## Evaluation (`eval/`)

`uv run eval` → `eval/reports/<ts>/report.{md,json}`. Fairness gate per §14.3
(`max_ratio 1.5`, needs ≥ 20 officer decisions in ≥ 2 chowkris). `--gate` exits
non-zero only on a measured failure or a ≥ 0.02 regression; BLOCKED never fails
the build and never prints a number.

## Status of Definitions of Done

| Phase | Status |
|---|---|
| 0 Scaffold | Done: compose up with PostGIS 3.4.3 + pgvector 0.8.6, pytest/ruff/mypy green, both Ollama models present, CI file pushed to `krish2105/virasat` |
| 1 Data | Manifest complete for everything on disk; pipeline produces pairs; quarantine reported; 10 landmarks spot-checked. LISS-4 and Mapillary BLOCKED. |
| 2 Vision | Code + tests done; training, calibration and every metric BLOCKED on labels |
| 3 RAG | Corpus parsed and indexed, hybrid retrieval live; precision@3 BLOCKED on 60 labelled pairs |
| 4 Agents | Five nodes, graph, checkpointer, loop cap tested; red-team catch rate BLOCKED |
| 5 API + DB | Done: migrations from empty, append-only audit enforced by trigger, decision round-trip tested |
| 6 Frontend | Done locally: keyboard queue, 3D scrub with fallback, e2e green; Lighthouse ≥ 95 to be run on the deployed URL |
| 7 Eval + docs | Harness done; README/VIVA after deploy; ablations BLOCKED on labels |
