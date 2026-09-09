# VIRASAT — Handoff (session 1 written 2026-09-09; updated end of session 2, same day)

Read this, then `CLAUDE.md`, then `docs/ARCHITECTURE.md`, then the plan file
`~/.claude/plans/full-stack-now-make-a-plan-jaunty-dusk.md` (if present; its content
is summarised below). Owner: Krishna Mathur (`krish2105`). Repo: github.com/krish2105/virasat.

## Owner decisions that override MASTER-PROMPT.md (do not re-litigate)

* Build **all phases in one continuous build**, with stop-checkpoints only where real
  data, human labelling, or spend is needed. Owner said: "i dont know anything you only do e2e" — make the technical calls, record them in ARCHITECTURE.md.
* Full pinned dependency stack installed up front. Plain docker-compose Postgres (no Supabase).
* Tiles by ground extent (320 m), Sentinel-2 + Google Open Buildings 2.5D Temporal; Mapillary for street imagery (blocked on token).
* Extra features approved and built: theme toggle (light/dark/system), officer login (self-hosted JWT + roles), Hindi UI, dossier PDF/CSV, notifications, audit viewer, per-building timeline, site-visit scheduler, model health dashboard.
* Deploy: **free tiers only** — Render free Postgres + free web service, Vercel Hobby. Render workspace id `tea-d995upu7r5hc73aqssgg` (My Workspace). Repo is public.
* Hard rules unchanged: no autonomous enforcement, evidence + clause per finding, never fabricate data (metrics print BLOCKED), fairness gate blocking, no personal data, verifier on a different model family.

## What is DONE and verified (all committed on `main`)

| Area | State | Proof |
|---|---|---|
| S0 scaffold | uv stack, `docker compose up` (Postgres 16 + PostGIS 3.4.3 + pgvector 0.8.6, **host port 5434**), CI yml, pre-commit gitleaks | `uv run pytest` 44 passed; ruff + mypy clean |
| S1 data | Sentinel-2 (2019-12-26, 2025-12-04), Open Buildings 2016–2023, OSM roads+7,579 buildings, WHC map 176277, JHCPR 2020 PDF; all in `data/MANIFEST.md` | `data/raw/*` on the owner's Mac only (data/ is gitignored except manifest, boundaries, evidence PNGs) |
| Boundaries | core 643 ha / buffer 1,994 ha georeferenced (ICP RMS 15.6 m); 9 chowkris derived | `data/boundaries/*.geojson` committed; `tests/unit/test_zoning.py` 10 landmarks pass |
| Pipeline | `uv run pipeline` → 780 tiles, quarantine 0.4 %, spatial splits | `data/processed/pipeline_report.json` (local) |
| RAG | 178 clause chunks, bge-m3 in pgvector (HNSW), hybrid+rerank retrieval | `python -m virasat.rag.chunk && python -m virasat.rag.index`; smoke query returns ACG-8 Demolition |
| Agents | 5 LangGraph nodes, Postgres checkpointer, loop cap; `uv run agents [--zone] [--change-type] [--limit]` | 9 fake-model tests; real Ollama run works for drop/escalate; assess path ran twice (see bugs) |
| Vision | Siamese/ViT/focal/temperature code; Open Buildings adapter → **103 candidates → 101 `changes` rows with evidence crops** | `python -m virasat.vision.open_buildings && python -m virasat.vision.infer` |
| API | FastAPI, JWT auth, queue/decisions, dossier json/csv/pdf, fairness, aggregate map, audit, timeline, visits, notifications, health | `tests/integration/test_api.py` 8 pass on `virasat_test` DB |
| Frontend | Next 15.5 / React 19 / Tailwind 3.4, dark palette, en/hi, keyboard queue, slider, 3D instanced massing + SVG fallback + reduced-motion slider, MapLibre aggregate map | `pnpm --dir web typecheck && pnpm --dir web lint`; **5/5 Playwright e2e pass** (`E2E_NO_SERVER=1 pnpm exec playwright test --project=desktop` with both servers running) |
| Eval | `uv run eval --gate` writes `eval/reports/<ts>/report.md`; everything BLOCKED honestly; exit 0 | run it |
| Docs | ARCHITECTURE, DATA_CARD, ETHICS, MODEL_CARD written | README, VIVA not yet |

Local dev servers: `.claude/launch.json` has `api` (uvicorn :8000) and `web` (next dev :3000). Officer for e2e: `e2e-officer` / `correct horse battery` (seeded in the local dev DB only; create with `uv run seed-admin`).

## Session 2 (2026-09-09, evening) — what changed

**All four session-1 bugs are closed, and three more were found by running the
system instead of its tests.**

| Was | Now |
|---|---|
| Bug 1: assess path crashed with `StringDataRightTruncation` | Fixed properly. The session-1 note claimed `route.py` filtered findings; it did not. `split_findings()` now stores only findings citing a retrieved clause, and puts the rest in the audit payload as `rejected_findings`. Reproduced first in `tests/integration/test_route_persist.py`. |
| Bug 2: 79 untriaged `outside` candidates | Cleared. All 82 now `dropped`, with no model call. |
| Bug 4: oversized definitions chunks "acceptable" | Not acceptable — they were the reason no finding could be stored. The two definitions sections (Regulations 3, ACG 11) were split per defined term into 41 pseudo-clauses with ids like `ACG-11 Should`. Still parsed into `clauses.jsonl`; **not indexed**. 178 parsed, 137 citable. |
| — | New: `assess.v1.md` produced invented clause *names*. `assess.v2.md` prints the allowed ids explicitly and demands a verbatim copy. |
| — | New: `evidence_ref` was only checked non-empty, so `"X"` satisfied the image-evidence hard rule. It must now equal the supplied crop. |
| — | New: `verify.v1.md` listed its tests as questions and llama3.1:8b answered them into `notes`, so five of seven rejections were statements of *compliance* returned with verdict `fail`. `verify.v2.md` requires violations only, indexed and quoted; a `fail` naming no finding is now invalid output. |
| CI never checked | It had failed on **every** push. `web/pnpm-workspace.yaml` was a stub with placeholder values and no `packages` field. Removed; the python job was always green. |

### First real batch result

101 candidates → **82 dropped** with no model call, **5 escalated direct**, **14
assessed**. 11 findings stored, every one citing a retrieved clause and a real
evidence crop; 12 drafts rejected before storage; **0 findings passed verification**.
The verifier rejects on substance, typically a topically related clause offered for a
specific claim. The owner chose to report this rather than re-run — it is the honest
headline and it is in the README.

13 of the 14 were verified under `verify.v1.md` and one under `v2`; `audit_log` records
prompt versions per row, so they are distinguishable.

### Owner decisions this session

* Hosted database: **Render free Postgres**, despite the 30-day deletion clock. The
  clock and the escape route are the first thing in `docs/DEPLOY.md`.
* Deploy split: **Claude does Vercel, owner does Render.**
* Labels: leave every metric BLOCKED; `label-clauses` verified working and documented.

## Remaining work

1. **Render (owner).** `render.yaml` is committed; `docs/DEPLOY.md` §1–4 and §6 are the
   steps. The migration now creates `postgis` and `vector` itself, so there is no
   extension step. Put the 30-day expiry in a calendar.
2. **Vercel Deployment Protection (owner, one toggle).** The build is live at
   `https://virasat-krishnamathur008-1499s-projects.vercel.app` but redirects visitors
   to a Vercel login. Settings → Deployment Protection → Vercel Authentication →
   Disabled. No CLI equivalent. (`virasat.vercel.app` is an unrelated project.)
3. **Env correction (owner or Claude).** `API_URL` / `NEXT_PUBLIC_API_URL` are set to
   `https://virasat-api.onrender.com`; correct them if Render appends a suffix, and set
   `CORS_ORIGINS` on Render to the Vercel origin.
4. **Lighthouse ≥ 95** on the deployed URL — cannot run until 2 is done.
5. **Labels (owner, blocking every metric):** 400 tile labels (`uv run label-tiles`),
   60 clause labels (`uv run label-clauses`). Nothing else unblocks the results table.
6. **Red-team set** `tests/fixtures/redteam/findings.jsonl` — still not built.
7. **`uv run digest`** is still a stub in `notify/digest.py`.
8. **Owner tasks carried over:** Bhoonidhi registration, Mapillary token, verify the
   chowkri names with the JNN Heritage Cell, `pre-commit install`.
9. **Still open from session 1:** the 3D scene has not been seen rendering in a real
   browser (SVG fallback works); the boundary is ~9.5 % small; `applies_to_change_type`
   is regex-derived.

**Trap to remember:** `python -m virasat.rag.index` deletes and rewrites `clauses`, and
`findings.clause_id` is a foreign key onto it. Re-index before an assessment run, never
after one.

## Commands that must stay green

```bash
docker compose up -d --wait db
uv run ruff check . && uv run mypy src && uv run pytest
uv run eval --gate
pnpm --dir web typecheck && pnpm --dir web lint
```
