# CLAUDE.md — VIRASAT

Read this before anything else, every session. Then read `MASTER-PROMPT.md`.

## What this project is

A heritage compliance and impact-assessment system for the Jaipur Walled City UNESCO
World Heritage property. It detects built-form change, checks it against byelaws, and
drafts assessments for a human heritage officer to approve, reject, or escalate.

## Hard rules — never violate these

1. **No autonomous enforcement.** Nothing this system produces goes to a citizen or an
   enforcement system. Every output is a recommendation to a named officer.
2. **No unsupported claims.** Every finding needs image evidence plus a byelaw clause
   citation. The verifier node blocks anything else. There is no bypass.
3. **Never fabricate data.** If a source is unreachable or a file is missing, stop and
   say so. Do not generate synthetic substitutes and continue. Fabricated data
   silently invalidates every metric downstream.
4. **Never skip the fairness gate.** Per-ward false-positive disparity is a blocking
   check, not a nice-to-have.
5. **No personal data.** No names, owners, tax records, or faces. Blur at ingest.

## How to work

- **State assumptions before coding.** If two readings of a task exist, present both.
  Do not pick one silently.
- **Simplest thing that works.** No speculative abstraction, no unrequested
  configurability, no error handling for impossible cases. If 200 lines could be 50,
  rewrite it.
- **Surgical edits.** Touch only what the task needs. Do not reformat or "improve"
  adjacent code. Every changed line traces to the current task.
- **Define the check first.** Turn each task into something verifiable before writing
  code.
- **Push back.** If something in `MASTER-PROMPT.md` is wrong, ambiguous, or
  overcomplicated, say so before implementing it.

## Phase discipline

One phase per session. Do not build ahead. State the Definition of Done explicitly at
the end of the session, and update `docs/ARCHITECTURE.md` before finishing.

Current phase: **all phases, single continuous build** (owner decision 2026-09-09 —
see `docs/ARCHITECTURE.md`). Phase DoDs remain as checkpoints; stop and report at every
`⛔` in the plan.

## Commands

```bash
uv sync                  # install
docker compose up -d     # Postgres + PostGIS + pgvector
uv run pytest            # tests
uv run ruff check .      # lint
uv run mypy src          # types
uv run pipeline          # data pipeline
uv run eval              # evaluation harness + fairness gate
uv run agents            # LangGraph batch over pending changes
uv run seed-admin        # first officer account
cd web && pnpm dev       # frontend
```

## Stack notes that are easy to get wrong

- Package manager is `uv`, not pip or poetry.
- Motion import is `motion/react`, **not** `framer-motion`.
- Map library is MapLibre, not Mapbox. No tokens.
- CRS is EPSG:32643 (UTM 43N).
- Splits are **spatial** (hold out whole chowkris), never random.
- The verifier must run on a different model from the assessor.
