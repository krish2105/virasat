# VIRASAT — Ethics statement

## What it does

Detects built-form change inside the Jaipur Walled City inscribed property and its buffer, checks each change against the Jaipur (Walled City) Heritage Conservation and Protection Regulations 2020, and drafts a citation-backed finding for a named heritage officer to approve, reject or escalate.

## What it explicitly does not do

* It never issues a notice, contacts a citizen, or writes to an enforcement system. There is no code path to any of those.
* It never ships a finding without an evidence crop and a clause citation. The verifier node blocks anything else, and mechanical checks run before the model is even asked.
* It never stores or infers ownership, tax, occupancy, names, or faces.
* It never fabricates data. A missing source stops the pipeline; a missing label prints BLOCKED instead of a number.

## Who is accountable

The officer who presses approve, reject or escalate. Every decision is recorded with their identity, a reason (mandatory for rejections), the git SHA, the model ids and the prompt versions that produced the draft — in an append-only table that the database itself refuses to update or delete.

## Known failure modes (measured or expected)

1. **The detector has not been trained.** No tile labels exist yet, so the Siamese model's recall, false-positive rate and calibration are BLOCKED. The queue currently runs on Open Buildings candidates whose confidence is not calibrated by us; the UI labels every such number "not calibrated".
2. **Retrieval precision is unmeasured.** 60 clause-pair labels are needed before precision@3 can be reported. Until then, an assessment can be grounded in a topically related but wrong clause; the verifier is the only defence and its catch rate is also BLOCKED.
3. **The chowkri names may be wrong.** Geometry is derived from streets; the naming follows the published description and has not been verified with the Heritage Cell. A misnamed ward does not change the fairness *ratio*, but it changes who the ratio is about.
4. **Mapping-effort bias.** Candidates are anchored on OpenStreetMap footprints. Better-mapped chowkris will produce more candidates regardless of what happened on the ground. The per-chowkri false-positive gate is designed to surface this, but only once officer decisions accumulate.
5. **Resolution.** Sentinel-2 (10 m) sees blocks, not houses. Facade alterations are invisible from orbit and street imagery is not yet ingested.
6. **Local models are weaker than cloud ones.** qwen2.5:14b and llama3.1:8b are the default; their JSON discipline is enforced by validation and retry, and two failed revisions route to a human rather than shipping.

## Fairness numbers

BLOCKED as of 2026-09-09: fewer than 20 officer decisions exist in any chowkri. The gate (`max FPR / min FPR ≤ 1.5`) is wired into `uv run eval --gate` and CI and will fail the build when it can be computed and is violated.

## The worst thing this could do if deployed carelessly

Flag poorer, better-mapped, or more recently surveyed neighbourhoods at a higher false rate, and lend that pattern the authority of a "detection". The design answers: a blocking per-ward disparity gate, a mandatory human decision with a mandatory reason on rejection, no enforcement surface, and a public map that shows counts per ward only.
