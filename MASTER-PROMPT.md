# MASTER-PROMPT.md — VIRASAT

**Heritage Compliance & Impact Assessment Intelligence for the Jaipur Walled City**

> Paste this file into a fresh Claude Code session as the build brief.
> Owner: Krishna Mathur · GitHub: `krish2105` · Target repo: `krish2105/virasat`
> Working directory: `~/Desktop/Projects/virasat`

---

## Table of contents

| # | Section |
|---|---|
| 1 | Mission and why this exists |
| 2 | Non-negotiable constraints |
| 3 | Problem statement and the user |
| 4 | Scope — in, out, and later |
| 5 | Tech stack (pinned) |
| 6 | Repository structure |
| 7 | Data sources and acquisition |
| 8 | Data pipeline specification |
| 9 | Vision model specification |
| 10 | Byelaw RAG specification |
| 11 | LangGraph node specification |
| 12 | Backend API specification |
| 13 | Frontend direction and specification |
| 14 | Evaluation harness |
| 15 | Observability, cost, and local-model routing |
| 16 | Security, privacy, and licensing |
| 17 | Build phases (session plan) |
| 18 | Definition of done per phase |
| 19 | Deliverables, README, and viva pack |

---

## 1. Mission and why this exists

Jaipur's Walled City was inscribed as a UNESCO World Heritage property in 2019 — a 710 ha property with a 2,205 ha buffer zone. In November 2025 the World Heritage Committee flagged a risk to the property's Outstanding Universal Value and asked the State Party to submit a detailed state-of-conservation report by **December 2026**, citing irregular development that is altering the city's original grid.

The evidence base for that report does not exist in any systematic form. The last comprehensive survey was a manual-and-drone exercise in 2019 that identified over 3,130 encroachments and illegal constructions. The Jaipur Nagar Nigam Heritage Regulation 2022 requires a Heritage Impact Assessment (HIA) — with a neutral third-party consultant — for interventions affecting Outstanding Universal Value. Every HIA today is a bespoke consultant report with no repeatable evidence base.

**VIRASAT is the evidence engine.** It continuously detects built-form change inside the property and buffer zone, checks each detected change against the applicable byelaw clause, and drafts a citation-backed Heritage Impact Assessment for a named human officer to approve, reject, or escalate.

Build the system so a Jaipur Development Authority or Jaipur Nagar Nigam heritage officer could actually use it. Not a demo.

---

## 2. Non-negotiable constraints

These are architectural requirements, not aspirations. Any design that violates one is wrong and must be redone.

1. **No autonomous enforcement.** VIRASAT never issues a notice, never contacts a citizen, never writes to any enforcement system. Every output is a recommendation addressed to a named officer, with a logged reason.
2. **No unsupported claim ships.** Every finding must carry (a) an image pair or crop as evidence and (b) a citation to a specific byelaw clause. The verifier node blocks anything else. There is no "best effort" path around this.
3. **Fairness is a blocking bug.** False-positive rate is computed and reported **per chowkri (ward)**. A disparity above the threshold in `config/fairness.yaml` fails the build. A model that over-flags poorer neighbourhoods is a discrimination engine, and shipping one is worse than shipping nothing.
4. **Every finding is reversible.** Officer rejections are stored with reasons and feed the retraining set. The audit log is append-only.
5. **No personal data.** No names, no owner records, no property-tax linkage, no faces. Street-level imagery must be face- and plate-blurred at ingest before it is written to disk. Building IDs are synthetic and internal.
6. **Local-first inference must work.** The system must run end-to-end with Ollama and no external LLM API. Cloud models are an optional speed path, never a hard dependency. This is a deliberate procurement-realism requirement.
7. **Reproducible.** Every model artifact, dataset snapshot, and eval run is versioned and re-runnable from a single command.

---

## 3. Problem statement and the user

### Formal problem statement

> Given time-separated overhead and street-level imagery of a defined heritage property, detect built-form changes, classify each change against a codified regulatory corpus, and produce a defensible, citation-backed Heritage Impact Assessment ranked by severity — with a mandatory human approval gate and published fairness metrics.

### Primary user — Heritage Officer, Jaipur Nagar Nigam

- Opens a weekly queue of detected changes, ranked by severity.
- Sees, for each: a before/after image pair, the detected change type, the zone (core vs buffer), the cited byelaw clause, and a drafted assessment.
- Acts: approve → goes to dossier; reject → goes to retraining set with a reason; escalate → flagged for site visit.
- Success for this user: the queue is short enough to clear in one sitting and trustworthy enough that approving is not a rubber stamp.

### Secondary user — State Party report author

- Needs an exportable, dated, sourced dossier covering the reporting window.
- Needs aggregate statistics: changes by type, by zone, by chowkri, by resolution status.

### Non-user

Citizens. VIRASAT has no citizen-facing enforcement surface. The public map (Phase 6) is read-only, aggregated, and shows no individual property attribution.

---

## 4. Scope — in, out, and later

### In scope (v1)

- Change detection over the 710 ha core + 2,205 ha buffer, 2019 baseline vs current.
- Four change classes: `NEW_CONSTRUCTION`, `VERTICAL_ADDITION`, `DEMOLITION`, `FACADE_ALTERATION`.
- Zone assignment (core / buffer / outside) from the inscribed boundary polygons.
- Byelaw RAG over the Heritage Regulation 2022 corpus and Architectural Control Guidelines.
- LangGraph pipeline: triage → retrieve → assess → verify → route to human.
- Officer review UI with approve / reject / escalate.
- Evaluation harness with fairness reporting.
- 3D web frontend with a scroll-driven time-scrub.

### Out of scope (v1)

- Interior changes, structural condition assessment, material analysis.
- Automatic notice generation, legal drafting, penalty calculation.
- Any integration with live municipal enforcement systems.
- Real-time detection. Weekly batch is the cadence.
- Ownership, tax, or occupancy data of any kind.

### Later (v2 candidates)

- Additional heritage properties (Ahmedabad, Champaner) by swapping the byelaw corpus.
- Crowdsourced officer field photos as a third sensing modality.
- Hindi interface via Bhashini.

---

## 5. Tech stack (pinned)

Use these versions. If one is unavailable, stop and report — do not silently substitute.

### Python (backend, ML, agents)

```
python                 3.11
uv                     (package manager — not pip, not poetry)
fastapi                0.115.*
uvicorn[standard]      0.32.*
pydantic               2.9.*
langgraph              0.2.*
langchain-core         0.3.*
langchain-ollama       0.2.*
langchain-anthropic    0.3.*        # optional cloud path
torch                  2.5.*
torchvision            0.20.*
timm                   1.0.*        # ViT + backbone zoo
rasterio               1.4.*
geopandas              1.0.*
shapely                2.0.*
pyproj                 3.7.*
opencv-python-headless 4.10.*
numpy                  1.26.*
pandas                 2.2.*
scikit-learn           1.5.*
psycopg[binary]        3.2.*
pgvector               0.3.*
sqlalchemy             2.0.*
alembic                1.14.*
pytest                 8.3.*
ruff                   0.7.*
mypy                   1.13.*
structlog              24.4.*
```

### Frontend

```
next                   15.x  (App Router)
react                  19.x
typescript             5.6.x
tailwindcss            3.4.x
motion                 12.x   # import from "motion/react" — NOT framer-motion
lenis                  1.1.x
three                  0.169.x
@react-three/fiber     8.17.x
@react-three/drei      9.114.x
maplibre-gl            4.7.x   # not mapbox — no token, no vendor lock
deck.gl                9.0.x
```

### Infrastructure

```
Postgres 16 + PostGIS 3.4 + pgvector   (Supabase local via supabase CLI)
Ollama                                  (qwen2.5:14b-instruct, llama3.1:8b)
Docker Compose                          (local orchestration)
GitHub Actions                          (CI: lint, type, test, eval)
Vercel                                  (frontend)
Render or Fly.io                        (backend)
```

**Why these:** MapLibre over Mapbox removes a token dependency and a vendor lock. `uv` over pip is faster and lockfile-native. Ollama proves on-prem capability, which is the actual procurement constraint for government-facing AI work in both India and the UAE. LangGraph over a bare chat loop because a heritage assessment is a state machine with checkpoints, not a conversation.

---

## 6. Repository structure

```
virasat/
├── CLAUDE.md                      # session rules — read this first, every session
├── MASTER-PROMPT.md               # this file
├── README.md                      # written LAST, in Phase 7
├── docker-compose.yml
├── pyproject.toml
├── uv.lock
│
├── config/
│   ├── settings.py                # pydantic-settings, env-driven
│   ├── zones.yaml                 # core/buffer polygon paths, CRS, chowkri names
│   ├── fairness.yaml              # per-ward FPR disparity thresholds
│   └── models.yaml                # model routing: which model for which node
│
├── data/                          # gitignored except manifests
│   ├── raw/                       # downloaded tiles, never edited
│   ├── interim/                   # aligned, tiled, normalised
│   ├── processed/                 # model-ready tensors + labels
│   ├── boundaries/                # core.geojson, buffer.geojson, chowkris.geojson
│   ├── corpus/                    # byelaw PDFs + extracted markdown
│   └── MANIFEST.md                # every file: source, licence, date, checksum
│
├── src/virasat/
│   ├── ingest/
│   │   ├── bhoonidhi.py           # ISRO open archive client
│   │   ├── sentinel.py            # Sentinel-2 fallback
│   │   ├── street.py              # street-level image loader + face/plate blur
│   │   └── align.py               # co-registration + tiling to fixed grid
│   ├── vision/
│   │   ├── siamese.py             # change-detection head
│   │   ├── facade.py              # ViT facade-alteration classifier
│   │   ├── train.py
│   │   └── infer.py
│   ├── geo/
│   │   ├── zoning.py              # point-in-polygon → core / buffer / outside
│   │   └── chowkri.py             # ward assignment for fairness slicing
│   ├── rag/
│   │   ├── chunk.py               # clause-aware chunking (NOT fixed-size)
│   │   ├── embed.py
│   │   ├── index.py               # pgvector schema + upsert
│   │   └── retrieve.py            # hybrid BM25 + dense, reranked
│   ├── agents/
│   │   ├── state.py               # the LangGraph state object
│   │   ├── graph.py               # graph assembly
│   │   ├── nodes/
│   │   │   ├── triage.py
│   │   │   ├── retrieve.py
│   │   │   ├── assess.py
│   │   │   ├── verify.py
│   │   │   └── route.py
│   │   └── prompts/               # every prompt as a versioned .md file
│   ├── api/
│   │   ├── main.py
│   │   ├── routes/
│   │   └── schemas.py
│   ├── db/
│   │   ├── models.py
│   │   └── migrations/
│   └── eval/
│       ├── datasets.py
│       ├── metrics.py
│       ├── fairness.py
│       └── run.py                 # `uv run eval` entrypoint
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
│
├── notebooks/                     # exploration only, never imported
│
├── web/                           # Next.js app
│   ├── app/
│   ├── components/
│   │   ├── city/                  # R3F scene
│   │   ├── queue/                 # officer review UI
│   │   └── ui/
│   ├── lib/
│   └── public/
│
└── docs/
    ├── ARCHITECTURE.md
    ├── DATA_CARD.md
    ├── MODEL_CARD.md
    ├── ETHICS.md
    └── VIVA.md
```

---

## 7. Data sources and acquisition

Every dataset must be recorded in `data/MANIFEST.md` with: source URL, licence, acquisition date, spatial extent, CRS, and SHA-256 checksum. **A dataset with no manifest entry does not exist.** Do not proceed to modelling on unmanifested data.

| Source | What | Access | Notes |
|---|---|---|---|
| **Bhoonidhi (NRSC/ISRO)** | ResourceSat-2/2A LISS-4, 5.8 m | Free after registration; API on request to NRSC | Highest-resolution open data for India — finer than Sentinel-2 |
| **Bhuvan** | Thematic layers, national base map, DEM | Free registration; WMS for direct mapping | Use WMS for the base layer, not for analysis |
| **Sentinel-2 (via Bhoonidhi or Copernicus)** | 10 m multispectral | Open | Fallback and temporal gap-filling |
| **NISAR daily processed** | S-SAR, from 08 Jul 2026 onward | Bhoonidhi | Stretch goal — SAR sees through cloud and haze. Novel; nobody has used this for heritage yet |
| **UNESCO WHC** | Inscription dossier, boundary description, state-of-conservation reports | whc.unesco.org, public | Property 710 ha, buffer 2,205 ha |
| **Heritage Regulation 2022** | Byelaws + Architectural Control Guidelines + HIA guidelines | Jaipur Nagar Nigam / annexures to the SoC report | **The RAG corpus.** Source it properly and cite the version |
| **OpenStreetMap** | Building footprints, street network, chowkri boundaries | ODbL | Attribution required in the footer |
| **2019 encroachment survey** | 3,130+ identified violations | Rajasthan Assembly Q&A record; press reporting | Ground-truth anchor for eval — see §14 |

### Acquisition rules

- Download once into `data/raw/`. Treat as immutable. Never edit in place.
- If an API needs credentials, put them in `.env`, never in code, and add a `.env.example`.
- If a source is unreachable, **stop and report it** — do not synthesise substitute data and continue silently. A fabricated dataset invalidates every metric downstream.
- If the byelaw PDF is not machine-readable, OCR it, then have a human spot-check 20 random clauses before indexing. Record the spot-check result in `DATA_CARD.md`.

---

## 8. Data pipeline specification

```
raw tiles ──▶ reproject ──▶ co-register ──▶ tile ──▶ normalise ──▶ pair ──▶ processed
```

### 8.1 Reprojection
All rasters to **EPSG:32643** (UTM 43N, correct for Jaipur). Store CRS in the manifest. Reject any input whose CRS cannot be read — do not guess.

### 8.2 Co-registration
Sub-pixel misalignment is the number-one cause of false positives in change detection. Register each epoch to the 2019 baseline using phase correlation on stable features (major road intersections). **Log the residual shift per tile.** Any tile with residual > 1.5 px is quarantined to `data/interim/quarantine/` and excluded from training and inference. Report the quarantine rate — it is a data-quality metric, not a nuisance.

### 8.3 Tiling
256×256 px tiles, 32 px overlap. Each tile carries: tile ID, centroid lat/lon, zone (`core` / `buffer` / `outside`), chowkri ID, epoch date.

### 8.4 Normalisation
Per-band standardisation using **statistics computed on the training split only**. Persist the statistics to `data/processed/norm_stats.json` and reuse them for validation, test, and inference. Recomputing per split is a leak.

### 8.5 Pairing
Emit `(tile_2019, tile_current, tile_id, metadata)`. Ensure both epochs are the same season where possible — vegetation phenology produces spurious change signal. Where seasons cannot be matched, record it in the metadata and check for a seasonal bias term during evaluation.

### 8.6 Street-level ingest
Faces and licence plates are blurred **at ingest, before the image is written to disk**. Not at display time. Not at export time. At ingest. Use a lightweight detector; err heavily toward over-blurring.

---

## 9. Vision model specification

### 9.1 Change detector — Siamese encoder

- Backbone: `timm` ResNet-50 or EfficientNet-B0, ImageNet-pretrained, **shared weights** across both branches.
- Head: absolute-difference feature map → 3×3 conv → BN → ReLU → 1×1 conv → 2-class logits (change / no-change).
- Loss: focal loss (α=0.25, γ=2.0). Change is rare; plain cross-entropy will converge to predicting "no change" everywhere and report 97% accuracy while being useless.
- Augmentation: flips, 90° rotations, small colour jitter. **No elastic or perspective warps** — they simulate exactly the misregistration artefact you are trying not to learn.
- Output: per-tile change probability + a change mask.

### 9.2 Facade classifier — ViT

- Backbone: `vit_small_patch16_224` from `timm`, fine-tuned.
- Classes: `COMPLIANT`, `UNAUTHORISED_FLOOR`, `MODERN_MATERIAL`, `SIGNAGE_VIOLATION`, `COLOUR_VIOLATION`.
- Runs only on street-level crops of tiles the change detector flagged. It is a second-stage refiner, not a first-stage scanner.

### 9.3 Calibration — do not skip

Raw softmax scores are not probabilities. Fit **temperature scaling** on the validation split and persist the temperature. The triage node's thresholds are meaningless on uncalibrated scores, and an officer who is told "87% confident" deserves that number to mean something. Report expected calibration error (ECE) in the model card.

### 9.4 Training discipline

- **Split spatially, not randomly.** Adjacent tiles overlap; a random split leaks the test set into training and inflates every metric. Hold out entire chowkris.
- Seed everything. Log seed, git SHA, and config hash with every run.
- Save checkpoints with the eval metrics embedded in the filename.

---

## 10. Byelaw RAG specification

### 10.1 Chunking — clause-aware, not fixed-size

Fixed-size chunking destroys regulatory text. A clause split mid-sentence retrieves as garbage and cites as garbage. Parse the corpus into a hierarchy:

```
Regulation → Section → Clause → Sub-clause
```

Each chunk = one clause or sub-clause, with the full ancestor path retained in its metadata. Chunk metadata:

```python
{
  "regulation": "Jaipur Nagar Nigam Heritage Regulation 2022",
  "section": "2",
  "clause": "2.4.1",
  "path": "Regulation 2022 > Architectural Control Guidelines > Main bazaars > Height",
  "applies_to_zone": ["core"],           # core, buffer, or both
  "applies_to_change_type": ["VERTICAL_ADDITION", "NEW_CONSTRUCTION"],
  "text": "...",
  "source_page": 34,
  "source_doc_sha256": "..."
}
```

`applies_to_zone` and `applies_to_change_type` enable **metadata pre-filtering**, which matters more than embedding quality here: a facade-colour clause should never be a candidate for a demolition finding, no matter how similar the embeddings are.

### 10.2 Retrieval — hybrid, filtered, reranked

1. Pre-filter by zone and change type (SQL `WHERE`, before vector search).
2. Hybrid: BM25 over clause text + dense over embeddings, reciprocal-rank fusion.
3. Rerank the top 20 to the top 5 with a cross-encoder.
4. Return top 5 with full metadata.

Store embeddings in pgvector. Index: HNSW, `m=16`, `ef_construction=64`.

### 10.3 Retrieval evaluation — build this before the agent

Hand-label 60 (change, applicable clause) pairs. This is tedious and it is the highest-value four hours in the project — you cannot tune retrieval you cannot measure. Report precision@3 and recall@5. **Target precision@3 ≥ 0.90.** If retrieval is below target, do not proceed to the assessment node: an agent grounded in wrong clauses generates fluent, confident, worthless output, and that is worse than no output.

---

## 11. LangGraph node specification

### 11.1 State object

```python
# src/virasat/agents/state.py
from typing import Literal, TypedDict
from datetime import date

class Evidence(TypedDict):
    before_crop_uri: str
    after_crop_uri: str
    change_mask_uri: str

class Clause(TypedDict):
    clause_id: str
    path: str
    text: str
    score: float

class Finding(TypedDict):
    claim: str                 # one sentence, one assertion
    clause_id: str             # MUST be non-empty
    evidence_ref: str          # MUST be non-empty
    severity: Literal["low", "medium", "high"]

class AssessmentState(TypedDict):
    # --- inputs (set by the pipeline, never by a model) ---
    change_id: str
    tile_id: str
    centroid: tuple[float, float]
    zone: Literal["core", "buffer", "outside"]
    chowkri_id: str
    epoch_before: date
    epoch_after: date
    change_prob: float               # calibrated
    change_type: str
    facade_class: str | None
    evidence: Evidence

    # --- populated by nodes ---
    triage_decision: Literal["assess", "drop", "escalate_direct"] | None
    triage_reason: str | None
    retrieved_clauses: list[Clause]
    draft_findings: list[Finding]
    verifier_verdict: Literal["pass", "fail"] | None
    verifier_notes: list[str]
    final_findings: list[Finding]
    routed_to: str | None

    # --- control ---
    revision_count: int              # hard cap 2
    errors: list[str]
```

### 11.2 The graph

```
       ┌─────────┐
       │  START  │
       └────┬────┘
            ▼
       ┌─────────┐   drop ──────────────────────┐
       │ triage  ├── escalate_direct ──┐        │
       └────┬────┘                     │        │
            │ assess                   │        │
            ▼                          │        │
       ┌─────────┐                     │        │
       │retrieve │                     │        │
       └────┬────┘                     │        │
            ▼                          │        │
       ┌─────────┐                     │        │
    ┌─▶│ assess  │                     │        │
    │  └────┬────┘                     │        │
    │       ▼                          │        │
    │  ┌─────────┐  fail &             │        │
    │  │ verify  ├── revisions < 2 ────┘        │
    │  └────┬────┘  (loop back to assess)       │
    │       │ pass, or fail & revisions == 2    │
    └───────┼───────────────────────────────────┘
            ▼
       ┌─────────┐
       │  route  │──▶ officer queue / dropped / escalated
       └────┬────┘
            ▼
          END
```

### 11.3 Node contracts

---

#### `triage` — cheap filter, no LLM

**Model:** none. This is deterministic Python.

Why: running an LLM on every tile in a 2,915 ha area is a cost and latency disaster, and the decision is a threshold check. Do not use a model where an `if` statement is correct.

```python
def triage(state: AssessmentState) -> dict:
    """Decide whether this change is worth assessing.

    Returns only the keys it modifies — LangGraph merges partial state.
    """
    # Outside the inscribed area, regulations do not apply.
    if state["zone"] == "outside":
        return {"triage_decision": "drop", "triage_reason": "outside inscribed area"}

    # Calibrated probability below floor: not enough signal to spend tokens on.
    if state["change_prob"] < 0.55:
        return {"triage_decision": "drop", "triage_reason": "below confidence floor"}

    # Demolition in the core zone is irreversible. It bypasses assessment
    # and goes straight to a human, because a 20-minute delay can matter.
    if state["change_type"] == "DEMOLITION" and state["zone"] == "core":
        return {"triage_decision": "escalate_direct",
                "triage_reason": "irreversible change in core zone"}

    return {"triage_decision": "assess", "triage_reason": "meets assessment criteria"}
```

---

#### `retrieve` — clause retrieval, no LLM

**Model:** embedding model + cross-encoder only.

Calls `rag.retrieve.hybrid_search()` with the metadata pre-filter from §10.2. Populates `retrieved_clauses`.

**If retrieval returns zero clauses after filtering**, do not fall through to the assessment node with an empty context. Set an error and route to human with the note "no applicable clause found — possible corpus gap". A corpus gap is a real finding about the regulation, and it is more useful surfaced than papered over.

---

#### `assess` — draft the findings

**Model:** `qwen2.5:14b-instruct` via Ollama (local default), or `claude-sonnet-4-6` if `VIRASAT_CLOUD=1`.

**Temperature: 0.1.** This is a compliance document, not prose.

**Output: strict JSON**, validated with a pydantic model. On a validation failure, retry once with the parse error appended to the prompt; on a second failure, record the error and route to human.

Prompt contract (`src/virasat/agents/prompts/assess.md`):

```
You are drafting a Heritage Impact Assessment finding for a heritage officer
of the Jaipur Nagar Nigam. Your draft will be reviewed by that officer before
any action is taken.

CONTEXT
Zone: {zone}
Change type: {change_type}
Detection confidence (calibrated): {change_prob}
Period: {epoch_before} to {epoch_after}
Facade classification: {facade_class}

APPLICABLE CLAUSES
{retrieved_clauses}

RULES
1. Every finding must cite exactly one clause_id from the list above.
   You may not cite a clause that is not listed.
2. Every finding must reference the supplied evidence.
3. One assertion per finding. Do not combine claims.
4. If the clauses provided do not support any finding, return an empty list.
   An empty list is a correct and valuable answer. Do not invent a finding
   to appear useful.
5. Do not recommend enforcement action, penalties, or legal remedies.
   You describe impact. The officer decides response.
6. Severity: low = reversible and minor; medium = reversible but materially
   affects streetscape; high = irreversible or affects Outstanding Universal Value.

Return JSON: {"findings": [{"claim": str, "clause_id": str,
                            "evidence_ref": str, "severity": str}]}
```

---

#### `verify` — adversarial check

**Model:** a **separate instance** with a different system prompt. If running cloud, use a different model than `assess`. Self-verification by the same instance in the same context is theatre — it agrees with itself.

The verifier receives the draft findings and the retrieved clauses, and is instructed to **attack** the draft:

```
You are auditing a draft heritage finding. Your job is to find reasons it
should NOT ship. You are not being helpful by approving it.

For each finding, check:
1. Is clause_id present in the supplied clause list? If not → FAIL.
2. Does the cited clause actually support the claim, or is it merely
   topically related? Topical relevance is not support → FAIL.
3. Does the claim assert anything not visible in the evidence
   (e.g. materials, intent, ownership, date of construction)? → FAIL.
4. Does the claim recommend enforcement? → FAIL.
5. Is the severity justified by the clause and evidence? If inflated → FAIL.

Return JSON: {"verdict": "pass"|"fail", "notes": [str],
              "failing_finding_indices": [int]}
```

Routing:
- `pass` → `route`
- `fail` and `revision_count < 2` → back to `assess` with `verifier_notes` appended, `revision_count += 1`
- `fail` and `revision_count == 2` → `route`, marked `needs_human_rewrite`. **Never ship a failing finding as if it passed.** Two failed revisions is itself a useful signal to the officer.

---

#### `route` — terminal, no LLM

Writes the outcome to Postgres and the append-only audit log:

| Path | Destination |
|---|---|
| `triage_decision == "drop"` | `dropped` table, retained for audit and eval |
| `triage_decision == "escalate_direct"` | officer queue, priority `urgent` |
| verifier `pass` | officer queue, priority by severity |
| `needs_human_rewrite` | officer queue, flagged, draft shown with verifier notes visible |

Every row carries: `change_id`, `git_sha`, `model_ids_used`, `prompt_versions`, `timestamp`, `total_tokens`. Reproducibility is not optional in a system that informs enforcement.

### 11.4 Graph assembly

```python
# src/virasat/agents/graph.py
from langgraph.graph import StateGraph, START, END

def build_graph():
    g = StateGraph(AssessmentState)

    g.add_node("triage", triage)
    g.add_node("retrieve", retrieve)
    g.add_node("assess", assess)
    g.add_node("verify", verify)
    g.add_node("route", route)

    g.add_edge(START, "triage")

    g.add_conditional_edges(
        "triage",
        lambda s: s["triage_decision"],
        {"assess": "retrieve", "drop": "route", "escalate_direct": "route"},
    )
    g.add_edge("retrieve", "assess")
    g.add_edge("assess", "verify")

    g.add_conditional_edges(
        "verify",
        # loop back only while revisions remain
        lambda s: "assess" if (s["verifier_verdict"] == "fail"
                               and s["revision_count"] < 2) else "route",
        {"assess": "assess", "route": "route"},
    )
    g.add_edge("route", END)

    return g.compile()
```

Use LangGraph's checkpointer so a batch run can resume after failure. Persist checkpoints to Postgres, not memory.

---

## 12. Backend API specification

FastAPI. All responses are pydantic models. No bare dicts.

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | Liveness + model availability |
| `POST` | `/runs` | Start a batch detection run over a date range |
| `GET` | `/runs/{run_id}` | Run status, progress, token spend |
| `GET` | `/queue` | Officer queue — filter by zone, severity, status |
| `GET` | `/changes/{change_id}` | Full detail: evidence URIs, clauses, findings, verifier notes |
| `POST` | `/changes/{change_id}/decision` | `{decision, officer_id, reason}` — approve / reject / escalate |
| `GET` | `/dossier` | Aggregated export for the reporting window (JSON + PDF) |
| `GET` | `/metrics/fairness` | Per-chowkri FPR, disparity ratio, threshold status |
| `GET` | `/map/aggregate` | Public read-only aggregate — **no individual attribution** |

Rules:
- `POST /changes/{id}/decision` requires a non-empty `reason` when the decision is `reject`. Rejections without reasons are useless for retraining.
- `/map/aggregate` returns counts per chowkri only. It must be impossible to identify a single property from this endpoint.
- Rate-limit `/runs`. A batch run is expensive.

---

## 13. Frontend direction and specification

### 13.1 The design thesis

**The city is the interface.**

Not a decorative 3D object. The hero is a navigable, extruded massing model of the actual Walled City, built from real footprints and elevation, with detected changes lit on it. If you swap the content out and the site still works for a fintech startup, it has failed.

**Explicitly forbidden** (these are the 2026 AI-generated tells, and a recruiter recognises them instantly):

- Dark navy backgrounds with purple-to-blue gradient blobs
- Glassmorphic cards applied everywhere
- Inter for both headings and body
- A floating abstract sphere or torus that does nothing
- Cream-and-terracotta serif combinations
- A single acid-green accent on near-black
- Effects stacked without a thesis

### 13.2 Design tokens

Derived from the actual city, not a palette generator.

```css
--sandstone:     #C1622E;   /* the pink city's actual pink */
--plaster:       #F2EBE0;   /* lime plaster */
--indigo:        #23304A;   /* Sanganeri block-print indigo */
--ink:           #1A1614;
--alarm:         #C4361F;   /* violations only — nowhere else */
--muted:         #8A8078;
```

One accent. `--alarm` appears only on a flagged change. If it shows up in the nav, delete it.

**Type:** a display face with real character for headings — a high-contrast serif or a grotesque with personality — paired with a mono for all data, coordinates, clause IDs, and dates. Never the same family for both. Load as variable fonts, `font-display: swap`.

**Layout system:** Jaipur is a grid-planned city of nine chowkris. Use that as the layout grid. Section dividers follow chowkri boundaries. The design now argues something instead of decorating.

### 13.3 The signature moment — time scrub

One scroll-linked moment, executed properly. Everything else is quiet.

- Lenis smooth scroll drives a `useScroll` progress value.
- Progress maps to a year between 2019 and 2026.
- Buildings extrude in as they appear; demolished structures fade to a wireframe ghost and stay visible as ghosts. **The absence is the point** — around 400 havelis have been lost, and a viewer should feel that.
- Camera dollies from oblique overview toward the core zone as progress increases.

Implementation notes:
- `motion` v12, import from `motion/react` — **not** `framer-motion`.
- Animate `transform` and `opacity` only. Never `width`, `height`, or `filter` on scroll.
- R3F scene lazy-loads behind `IntersectionObserver`. The page must be fully readable and useful with WebGL absent — ship a static isometric SVG fallback that looks intentional, not broken.
- Gate the entire sequence behind `useReducedMotion()`. Reduced-motion users get a year slider they control, not a stripped page.
- Instance the building meshes. Thousands of individual meshes will tank frame rate; `InstancedMesh` will not.

### 13.4 Officer queue UI

This is the part a real user touches, so it is designed for speed, not beauty.

- Dense list. Severity as a left border, not a badge cloud.
- Before/after image pair with a draggable comparison slider.
- Cited clause shown in full, expandable to the ancestor path.
- Three keyboard-first actions: `A` approve, `R` reject, `E` escalate. Reject opens a required reason field.
- Verifier notes always visible when present. Never hide the system's own doubts from the person accepting responsibility.
- Calibrated confidence shown as a number with its calibration date, not a vague bar.

### 13.5 Quality bar (all must pass)

- Responsive to 360 px. No horizontal scroll, no clipping.
- Keyboard accessible: real `<button>`/`<a>`, visible focus rings, logical tab order.
- `prefers-reduced-motion` respected throughout.
- 60 fps on a mid-range Android for the scroll sequence.
- Body text contrast ≥ 4.5:1.
- Semantic heading hierarchy, `alt` text on every evidence image, landmarks.
- No layout shift from animation.
- OSM attribution in the footer. It is a licence condition, not a courtesy.

---

## 14. Evaluation harness

`uv run eval` produces `eval/reports/<timestamp>/report.md` plus JSON. It runs in CI. **A metrics regression fails the build.**

### 14.1 Ground truth

Three sources, in descending order of strength:

1. **The 2019 survey anchor.** 3,130+ identified encroachments. Where locations are recoverable, these are positives.
2. **Hand-labelled tiles.** Label 400 tile pairs yourself: 200 change, 200 no-change, stratified across all nine chowkris. Non-negotiable — do it before training, not after.
3. **Officer decisions.** Once the queue is live, approvals and rejections are the strongest label source. Feed them back.

### 14.2 Metrics

| Layer | Metric | Target | Rationale |
|---|---|---|---|
| Change detection | Recall | ≥ 0.85 | A missed demolition is the costly error |
| Change detection | False-positive rate | ≤ 0.15 | Officer trust collapses above this |
| Change detection | ECE (calibration) | ≤ 0.05 | Confidence numbers must mean something |
| Facade classifier | Macro-F1 | ≥ 0.75 | Classes are imbalanced; macro, not micro |
| Retrieval | Precision@3 | ≥ 0.90 | Wrong clause = worthless finding |
| Retrieval | Recall@5 | ≥ 0.85 | Missing the governing clause is silent failure |
| Assessment | Citation groundedness | ≥ 0.95 | Every claim traces to a supplied clause |
| Verifier | Catch rate on injected errors | ≥ 0.80 | See §14.4 |
| End-to-end | Officer agreement rate | Track, no target | The only metric that ultimately matters |

### 14.3 Fairness — the blocking gate

```python
# src/virasat/eval/fairness.py
def fairness_gate(fpr_by_chowkri: dict[str, float], max_ratio: float) -> bool:
    """FPR disparity ratio across wards. Returns False to FAIL the build.

    A model that flags one neighbourhood at three times the false rate of
    another is not a heritage tool, it is a discrimination engine. This
    gate is why the check runs in CI and not in a notebook.
    """
    vals = [v for v in fpr_by_chowkri.values() if v > 0]
    if len(vals) < 2:
        return True                       # not enough wards to compare
    return (max(vals) / min(vals)) <= max_ratio
```

Set `max_ratio: 1.5` in `config/fairness.yaml`. Publish the per-ward table in the README. Publishing an imperfect number is credible; hiding it is not.

### 14.4 Adversarial eval — earn the verifier

Build a red-team set of 50 deliberately broken findings:

- Cites a clause that was not retrieved
- Cites a real clause that is topically related but does not support the claim
- Asserts material, ownership, or intent not visible in the evidence
- Recommends enforcement action
- Inflates severity beyond what the clause warrants

Measure the verifier's catch rate. **Below 0.80, the verifier is decorative** and you must say so in the README rather than claim a safety property you do not have.

### 14.5 Ablations to report

Run these and put the table in the README. They are what a senior interviewer will ask about.

| Ablation | Question it answers |
|---|---|
| No metadata pre-filter | How much does filtering beat pure embedding similarity? |
| Fixed-size vs clause-aware chunking | Was the chunking work justified? |
| No verifier node | What does the safety layer actually cost and buy? |
| Local Qwen vs cloud Sonnet | Is the on-prem story credible on quality, or only on privacy? |
| Random vs spatial split | Quantify the leak. Report both numbers. |

---

## 15. Observability, cost, and local-model routing

- `structlog` JSON logging. Every node logs: `change_id`, node name, model ID, prompt version, token counts, latency, outcome.
- Token spend per run surfaced at `GET /runs/{run_id}`. An agent system whose cost you cannot see is not production-ready.
- `config/models.yaml` routes model per node so the local/cloud switch is one config change, not a code change:

```yaml
nodes:
  assess:
    local:  {provider: ollama,    model: qwen2.5:14b-instruct, temperature: 0.1}
    cloud:  {provider: anthropic, model: claude-sonnet-4-6,     temperature: 0.1}
  verify:
    local:  {provider: ollama,    model: llama3.1:8b,           temperature: 0.0}
    cloud:  {provider: anthropic, model: claude-opus-5,         temperature: 0.0}
default_mode: local
```

Note the verifier uses a **different model family** from the assessor in both modes. That is the point of it.

---

## 16. Security, privacy, and licensing

- Secrets in `.env` only. Ship `.env.example`. Never commit real credentials; add a pre-commit secret scan.
- Face and plate blurring at ingest (§8.6), enforced by a test that fails if an unblurred image reaches `data/processed/`.
- No ownership, tax, occupancy, or personal records enter the system at any stage.
- Public endpoints are aggregate-only and must not permit re-identification of a single property.
- Audit log is append-only. Add a DB constraint; do not rely on convention.
- Record licence for every dataset in `MANIFEST.md`. OSM requires ODbL attribution in the UI footer.
- `docs/ETHICS.md` states plainly: what the system does, what it explicitly does not do, its known failure modes, its measured fairness numbers, and who is accountable for a decision. Write it honestly. A limitations section that admits real weaknesses is the strongest credibility signal in the repo.

---

## 17. Build phases (session plan)

One phase per Claude Code session. Do not start a phase before the previous one's Definition of Done passes. **Do not build ahead.**

| Phase | Focus | Output |
|---|---|---|
| **0** | Scaffold | Repo, `uv` env, Docker Compose (Postgres + PostGIS + pgvector), Ollama pulled, CI skeleton, `CLAUDE.md` |
| **1** | Data | Boundaries loaded, tiles acquired, `MANIFEST.md` complete, pipeline through `processed/`, quarantine rate reported |
| **2** | Vision | Siamese trained, calibrated, spatially split, metrics hitting §14.2 targets or an honest report of why not |
| **3** | RAG | Corpus parsed to clause hierarchy, indexed, hybrid retrieval, 60 labelled pairs, precision@3 ≥ 0.90 |
| **4** | Agents | LangGraph implemented per §11, all five nodes, checkpointing, red-team set built, verifier catch rate measured |
| **5** | API + DB | FastAPI per §12, migrations, audit log, officer decision loop working end to end |
| **6** | Frontend | Next.js, officer queue first (it is the real product), then the 3D time scrub |
| **7** | Eval + docs | Full eval report, ablations, fairness table, README, model card, data card, ethics doc, deploy |

### Working rules for every session

Derived from the Karpathy guidelines — these are behavioural requirements, not suggestions.

1. **Think before coding.** State assumptions explicitly. If two interpretations exist, present both — do not pick silently. If a simpler approach exists, say so and push back.
2. **Simplicity first.** Minimum code that solves the problem. No speculative abstractions, no configurability nobody asked for, no error handling for impossible scenarios. If 200 lines could be 50, rewrite it.
3. **Surgical changes.** Touch only what the task requires. Do not "improve" adjacent code or reformat files you happened to open. Every changed line must trace to the current task.
4. **Goal-driven.** Turn each task into a verifiable check before writing code: "add validation" → "write tests for invalid inputs, then make them pass."
5. **Stop on missing data.** If a source is unreachable or a file is absent, say so and stop. Never fabricate data to keep moving. Fabricated data invalidates every downstream metric silently, which is the worst possible failure mode for this project.
6. **Update `docs/ARCHITECTURE.md` at the end of every phase**, before the session ends.

---

## 18. Definition of done per phase

Each phase ships only when every box is checked. State them explicitly at the end of the session.

**Phase 0** — `docker compose up` brings up Postgres with PostGIS and pgvector; `uv run pytest` passes on an empty suite; `ollama list` shows both models; CI runs ruff + mypy green.

**Phase 1** — `MANIFEST.md` covers every file with source, licence, date, checksum. `uv run pipeline` produces tile pairs. Co-registration residuals and quarantine rate are logged and reported. Boundary polygons load and zone assignment is spot-checked against 10 known landmarks.

**Phase 2** — Model trained on a spatial split. `eval/reports/` contains recall, FPR, ECE. Calibration temperature persisted. Model card drafted. Random-split and spatial-split numbers both reported so the leak is quantified.

**Phase 3** — Corpus parsed to clause hierarchy with the ancestor path preserved. 60 labelled pairs committed. Precision@3 ≥ 0.90 or an explicit written statement of what is blocking it.

**Phase 4** — All five nodes implemented and unit-tested. Graph compiles, checkpoints to Postgres, resumes after a killed process. Revision loop caps at 2 and is tested. Red-team set of 50 committed; verifier catch rate measured and reported.

**Phase 5** — All endpoints per §12 return validated pydantic models. Migrations run clean from empty. Audit log append-only constraint enforced at the DB level and tested. Officer decision round-trips and lands in the retraining set.

**Phase 6** — Frontend hits every item in §13.5. Officer queue is keyboard-operable end to end. 3D scene lazy-loads with a working static fallback. Lighthouse accessibility ≥ 95.

**Phase 7** — Full eval report with all five ablations. Fairness table published in the README with real numbers. README, `MODEL_CARD.md`, `DATA_CARD.md`, `ETHICS.md`, `VIVA.md` complete. Deployed and reachable.

---

## 19. Deliverables, README, and viva pack

### README structure

Written in Phase 7, not before. A README written first describes intentions; one written last describes a system.

1. One-paragraph problem statement with the December 2026 deadline named.
2. The architecture diagram.
3. What it does **not** do — the §2 constraints, stated up front. Putting limitations near the top rather than buried at the bottom is itself the credibility signal.
4. Results table with real numbers from `eval/reports/`.
5. **Fairness table, per chowkri.** Publish it whatever it says.
6. Ablations table.
7. Quickstart: clone → `docker compose up` → `uv sync` → `uv run pipeline` → `uv run eval` → `pnpm dev`.
8. Data sources with licences.
9. Known limitations, written honestly.

### `docs/VIVA.md`

Write answers to at least these:

- Why LangGraph rather than a single prompt or a simple chain?
- Why does the verifier use a different model from the assessor?
- What happens when the model flags a legal building, and how do you know how often that happens?
- Why spatial splitting, and how much did it change the numbers?
- Why calibrate, and what does the confidence number mean to an officer?
- Why clause-aware chunking rather than fixed-size?
- Why does local inference matter for this deployment?
- How does this transfer to another heritage city, and what stays fixed?
- What is the worst thing this system could do if deployed carelessly, and what in the design prevents it?
- What would you do differently with six more months?

### Portfolio artifacts

- Live deployment URL.
- 90-second screen recording: detection → clause citation → officer decision → dossier export.
- One architecture diagram, exported clean.
- A short LinkedIn write-up leading with the deadline and the fairness table, not with the tech stack.

---

## Final instruction to Claude Code

Read `CLAUDE.md`, then this file, then state your understanding of Phase 0 and the assumptions you are making, and wait for confirmation before writing code.

Do not build ahead of the current phase. Do not fabricate data. Do not skip the fairness gate. If something in this document is ambiguous or wrong, say so before implementing it rather than guessing — an assumption stated is cheap, an assumption buried is expensive.
