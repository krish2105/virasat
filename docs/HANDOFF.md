# VIRASAT — Handoff (written 2026-09-09, end of session 1)

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

## Known bugs / loose ends (do these first)

1. **Assess path crashed on a real run** with `StringDataRightTruncation (varchar 64)` — the local model returned a clause_id longer than 64 chars. Fixed in `agents/nodes/route.py` (only findings citing a retrieved clause are stored; raw drafts go to the audit payload) but **not yet re-run**. Re-run: `uv run agents --limit 1 --zone core --change-type VERTICAL_ADDITION`, then inspect `findings` and `audit_log`. Also consider logging the raw model output at debug level.
2. Queue still holds ~79 `outside`-zone candidates with `triage_decision NULL` (the owner declined the bulk triage run). Run `uv run agents --limit 100 --zone outside` (no LLM, they drop) then `--zone buffer` / `--zone core` (LLM, ~1 min per change on qwen2.5:14b).
3. The in-app browser lost the WebGL context; the scene now falls back to SVG on `webglcontextlost` and with `?nogl=1`. Verify the 3D scene visually in a real browser; not yet seen rendering.
4. `chunk.py` leaves four oversized chunks (definitions, ACG-7); acceptable but could be split further.
5. Chowkri **names** are an assumption (see DATA_CARD) — flag to the owner for Heritage Cell verification.

## NOT done (remaining plan, in order)

1. **Deploy (S10, free tiers)** — files are ready: `requirements-api.txt` (slim, no torch), `settings.cookie_secure`, evidence PNGs committed. Steps:
   a. Render: `create_postgres` (plan free, region singapore or oregon, version 16) → enable `postgis` + `vector` (may need dashboard; `query_render_postgres` is read-only) → `DATABASE_URL=<external url> uv run alembic upgrade head` from the Mac → copy data: `pg_dump --data-only -t officers -t runs -t tiles -t buildings -t changes -t clauses -t findings -t decisions -t audit_log` from local (port 5434) and restore.
   b. Render web service via MCP `create_web_service` (runtime python, repo `https://github.com/krish2105/virasat`, buildCommand `pip install uv && uv pip install --system -r requirements-api.txt && uv pip install --system --no-deps .`, startCommand `uvicorn virasat.api.main:app --host 0.0.0.0 --port $PORT`, env: `DATABASE_URL`, `JWT_SECRET`, `COOKIE_SECURE=1`, `CORS_ORIGINS=<vercel url>`, `VIRASAT_CLOUD=0`). Note `/health` reports ollama=false there (expected; `mode` local without Ollama → status degraded; consider a `VIRASAT_API_ONLY=1` flag to report ok).
   c. Vercel: deploy `web/` (root directory `web`), env `API_URL` + `NEXT_PUBLIC_API_URL` = Render URL. The Vercel MCP `list_teams` was rate-blocked at handoff time; `vercel` CLI or `create_git_project` also work.
   d. Seed an officer on the hosted DB with `DATABASE_URL=... uv run seed-admin <name>`; run Lighthouse (a11y ≥ 95) on the Vercel URL.
2. **README.md** (written last; structure in MASTER-PROMPT §19: deadline paragraph, architecture diagram, limitations up top, results table with BLOCKED cells, fairness table, ablations table BLOCKED, quickstart, sources+licences). Also remove `readme =` absence: pyproject currently has no readme field on purpose.
3. **docs/VIVA.md** — answer the ten §19 questions from the real design (ICP georeferencing, metre tiles, verifier family split, BLOCKED discipline, chowkri-name risk).
4. **Red-team set** `tests/fixtures/redteam/findings.jsonl` (50 broken findings against fixture clauses) — not built yet; catch-rate stays BLOCKED until 60 clause labels exist anyway.
5. **Notifications digest** `uv run digest` is still a stub (`notify/digest.py`); in-app notifications on escalation work.
6. Owner tasks (blocking metrics): Bhoonidhi registration, Mapillary token, 400 tile labels (`uv run label-tiles`), 60 clause labels (`uv run label-clauses`), verify chowkri names, `pre-commit install`.
7. CI on GitHub has not been checked since the first push — look at the Actions tab; the `web` job needs `pnpm-lock.yaml` (committed) and the python job needs Docker for compose (available on ubuntu runners).

## Commands that must stay green

```bash
docker compose up -d --wait db
uv run ruff check . && uv run mypy src && uv run pytest
uv run eval --gate
pnpm --dir web typecheck && pnpm --dir web lint
```
