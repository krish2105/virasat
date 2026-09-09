# VIRASAT — viva pack

Answers to the ten questions in `MASTER-PROMPT.md` §19, written from the system as
built. Where a question asks for a number that does not exist yet, the answer says so
and says what would produce it. Nothing here is estimated.

---

## 1. Why LangGraph rather than a single prompt or a simple chain?

Because the control flow is a graph and pretending otherwise would hide the parts that
matter.

Three properties a chain cannot express:

**A cycle with a cap.** The verifier can reject a draft and send it back to the
assessor. That is a loop, and an uncapped loop against a local model is an unbounded
bill and an unbounded wait. `MAX_REVISIONS = 2`; two failures route to
`needs_human_rewrite`. The cap is a graph edge condition, tested directly
(`test_graph_revision_loop_caps_at_two_and_routes_to_human`).

**Edges that skip the model entirely.** `triage` is pure Python with no LLM. Of the 101
candidates in the database, 82 are outside the buffer zone and leave the graph at the
first node without a single token being generated; demolitions in the core skip
assessment in the other direction, straight to an officer as urgent. That saving is
structural. In a chain it would be a prompt instruction the model could ignore.

**A refusal to run on an empty context.** If retrieval returns nothing, the graph
routes to a human rather than falling through to the assessor. A chain's linear edge
would hand the model an empty clause list and invite it to invent one — which is
exactly the failure this system exists to prevent.

Two properties that are operational rather than architectural, but decided it: the
Postgres checkpointer means a batch interrupted at change 9 of 14 resumes rather than
restarting, and each node's inputs and outputs are separately inspectable, so when the
assess path failed this session it was possible to say *which node* produced the bad
value rather than guessing at one long prompt.

## 2. Why does the verifier use a different model from the assessor?

Because a model asked to check its own work agrees with itself. The errors are
correlated: the same tokeniser, the same training data, the same tendency to find a
plausible-sounding clause name convincing. A self-check mostly measures fluency.

The split is enforced, not intended. `assert_distinct_families()` runs before the batch
starts and raises if `assess` and `verify` resolve to the same model family — locally
qwen2.5:14b assesses and llama3.1:8b verifies; in cloud mode claude-sonnet-5 assesses
and claude-opus-5 verifies.

The more important half of the answer is that the verifier is **not only a model**.
Three deterministic checks run before any second model is invoked, and a finding that
fails them never reaches the verifier LLM at all:

* the cited `clause_id` must be one that retrieval actually returned;
* `evidence_ref` must be the supplied crop, not a description of it;
* the claim must contain no enforcement language.

This session demonstrated why the mechanical layer carries the weight. The local 14B
assessor was citing clause *names* it had invented — "Architectural Styles",
"Materials and Colours". Ten such findings were caught by the deterministic rule and
logged as `rejected_findings`; a peer model asked "is this a reasonable finding?" would
plausibly have said yes, because as prose it reads fine. The model verifier catches
what the rules cannot phrase: overreach, combined claims, assertions about materials or
intent that the image does not support.

## 3. What happens when the model flags a legal building, and how do you know how often that happens?

**What happens:** nothing, until an officer acts. The candidate appears in the officer
queue as a recommendation with its evidence crops and its cited clause. The officer
rejects it; the API returns 422 if no reason is given, so a rejection cannot be a
silent click. The rejection is written to `decisions` and to `audit_log`, which has
BEFORE UPDATE/DELETE/TRUNCATE triggers that raise — proven by test — so the record of
the false positive cannot later be tidied away. Rejected candidates are the retraining
set.

There is no path from this system to a citizen or to an enforcement system. That is a
design constraint, not a configuration.

**How often: BLOCKED.** The false-positive rate needs officer decisions on a
representative sample, and the per-ward disparity gate needs at least 20 decisions
spread over at least two chowkris. The database holds 3 decisions. Until that
threshold is reached `uv run eval` prints BLOCKED rather than a number, and the gate
neither passes nor fails — it abstains. A rate computed from 3 decisions would be
worse than no rate, because it would be quoted.

## 4. Why spatial splitting, and how much did it change the numbers?

**Why:** adjacent tiles in a walled city are not independent samples. They share
buildings that straddle the tile edge, the same acquisition, the same sun angle and
shadow direction, the same sensor artefacts, and often the same construction episode —
one contractor, one street, one year. A random tile split puts one half of a building
in train and the other in test, and the model scores well by recognising the building
rather than the change. The split is therefore by whole chowkri (and by buffer sector
outside the core): 431 train / 214 val / 135 test tiles, defined in `config/splits.yaml`.

**How much did it change the numbers: BLOCKED.** Reporting the gap between a random
split and a spatial split requires a trained detector, and training requires 400 tile
labels that do not exist. `vision/train.py` refuses to run below 100 labels rather than
producing a model whose metrics would be meaningless. The comparison is the single most
useful ablation this project could publish and it is the first thing to run once labels
exist.

## 5. Why calibrate, and what does the confidence number mean to an officer?

A neural network's output is a score, not a probability. Softmax and sigmoid outputs
are systematically overconfident, and the number is what an officer will use to decide
whether to spend a site visit on a candidate. If the interface prints 0.87 and the
officer reads that as "seven in eight of these are real", the number has to earn that
reading.

So: temperature scaling fitted on the validation split, with expected calibration error
reported. Calibrated, 0.87 means *among the candidates scored 0.87, roughly 87 per cent
are genuine changes* — a statement about a population the officer can act on, not a
statement about this one building.

**Status: BLOCKED.** No labels, no fitted temperature, no ECE. The honest consequence
is that the confidence figure currently shown is an uncalibrated model score, and the
system must not present it to an officer as a probability until the calibration run has
happened. The `calibration_date` column on `changes` exists so that a calibrated score
is distinguishable from an uncalibrated one at the row level rather than by memory.

## 6. Why clause-aware chunking rather than fixed-size?

Because the citation is the product. A finding is worthless — worse, it is dangerous —
unless it points at a specific provision an officer can look up in the notified
regulation. A fixed 512-token window cuts across clause boundaries, so the best it can
offer is "somewhere in this passage", and it hands the model two half-clauses to blend
into one confident sentence.

The parser therefore follows the document's own structure: the Regulations' clause and
sub-clause numbering, the Architectural Control Guidelines' sections and subsections,
and enumerated items as siblings under their parent clause. Each chunk carries its full
ancestor path, its source page and the SHA-256 of the source PDF, so a citation is
traceable to a page of a specific file.

This session produced a sharp illustration of the failure mode at the other end of the
same problem. The chunker was splitting the two **definitions** sections (Regulations 3
and ACG 11) at each defined term, generating identifiers from the term text: `ACG-11
Should`, `ACG-11 Chajja`, `ACG-11 New  Construction`. That is 41 of 178 chunks. Two
things were wrong with it. An identifier derived from body text is not stable — the
double space in `ACG-11 New  Construction` came from the PDF's line breaking, and no
model will reproduce it verbatim. And a glossary entry is not a provision: you cannot
cite the definition of "Chajja" as the byelaw a building breached. `ACG-11 Should` was
occupying a top-five retrieval slot for a core vertical addition, and the assessor,
shown it as a permitted citation, collapsed it to `ACG-11` — an invalid citation, and
the reason no finding could be stored. The definitions sections are still parsed and
still recorded in `clauses.jsonl`, but only the 137 normative clauses are indexed as
citable.

The general rule: clause identifiers come from the document's numbering, never from its
prose, and only normative text is citable.

## 7. Why does local inference matter for this deployment?

**Data.** The imagery covers a lived-in city. Even with faces and plates blurred at
ingest, sending street-level and sub-metre building imagery of a specific ward to a
commercial API is a disclosure the municipality has not agreed to. Local inference
means the question does not arise.

**Cost, and what cost does to auditing.** The fairness gate is worth having only if it
is run often — after every model change, every prompt change, every corpus reindex. On
a metered API, re-running the audit has a price, and anything with a price gets run less
often than it should. Locally an audit costs electricity.

**Institutional reality.** The intended operator is a municipal heritage cell. Its
procurement, its network policy and its budget line are not shaped like a per-token API
contract. A system that needs one is a system that does not get deployed.

The consequence, accepted deliberately: Render hosts the API and the database only. The
pipeline, the vision layer and the agent graph run on the owner's machine against the
same `DATABASE_URL`. No free tier hosts a 14B model, and the alternative — moving
inference to a cloud API to make the demo self-contained — would trade the property
being defended for a convenience.

## 8. How does this transfer to another heritage city, and what stays fixed?

**Fixed:** the graph and its edges; the two-model split with the mechanical checks in
front; the contract that a finding needs image evidence plus a clause citation, enforced
at the database by a foreign key rather than by prompt; the human-approval gate; the
append-only audit; the blocking fairness gate; and the BLOCKED discipline that keeps
unmeasured quantities out of the report.

**Replaced per city:** the corpus (one notified regulation PDF and a parser for its
numbering scheme); the boundary and its georeferencing; the ward or block partition the
splits and the fairness gate are computed over; the change-type taxonomy; the CRS; the
imagery sources and their revisit cadence.

**The honest difficulty** is not the code. It is that the transfer needs a machine-
readable notified regulation with stable clause numbering, and an administrative
partition meaningful enough that per-ward disparity means something. Jaipur has both:
the JHCPR 2020 is a clean vector PDF, and the chowkri grid is the city's own
organising unit. A city whose regulation exists only as a scanned annexure, or whose
wards were drawn without regard to built form, is a materially harder problem — and the
current chowkri **names** here are themselves an unverified inference from the published
grid description, flagged in `docs/DATA_CARD.md` pending confirmation by the JNN
Heritage Cell.

## 9. What is the worst thing this system could do if deployed carelessly, and what in the design prevents it?

**The worst outcome is a demolition ordered on a hallucinated clause.** An automated
notice, citing a provision that does not exist or does not apply, against a building
whose owner has no practical way to contest a machine — in a property where the loss is
irreversible and counts against Outstanding Universal Value.

What stands in the way, in order of how much each is relied on:

1. **There is no output path.** Nothing in this system emits to a citizen or an
   enforcement system. The terminal node writes to a queue a named officer reads.
2. **A finding cannot exist without a real citation.** `findings.clause_id` is a
   foreign key onto the corpus. This session proved the constraint is load-bearing
   rather than decorative: the assessor's invented clause names hit it and the process
   died. It was fixed by refusing to store such findings and logging them instead — not
   by relaxing the constraint.
3. **A finding cannot exist without the evidence crop**, and the reference must be the
   crop itself, not a sentence describing one.
4. **Enforcement language is a mechanical failure**, before any model opinion.
5. **A second model, of a different family, adversarially reviews what survives.**
6. **An officer approves, rejects with a mandatory reason, or escalates**, and the
   decision is written to an audit log that cannot be updated or deleted, carrying the
   git SHA, model ids and prompt versions that produced the recommendation.

**The second-worst outcome is quieter and more likely:** the system works, is trusted,
and applies unequal pressure across chowkris — more scrutiny where imagery is better,
where buildings are denser, where the detector happens to fire more. Nobody notices,
because each individual recommendation is defensible. That is what the per-ward
false-positive disparity gate exists for, why it blocks rather than warns, and why the
fairness table goes in the README whatever it says.

## 10. What would you do differently with six more months?

**Labels, first and without competition.** 400 tile labels and 60 clause-pair labels.
Every BLOCKED cell in the README traces back to their absence, and no amount of
additional engineering converts a blocked metric into a real one. The eval harness,
the calibration code, the fairness gate and the ablation scaffolding are all written and
all idle.

**Then, roughly in order:**

* Verify the chowkri names with the JNN Heritage Cell, and treat the boundary's 9.5 per
  cent area shortfall against the inscribed 710/2,205 ha as a georeferencing problem to
  close rather than a discrepancy to document.
* Build the red-team set — 50 deliberately broken findings — and report a catch rate.
  It is the only direct measurement of whether the verifier works, and right now the
  claim rests on unit tests over a scripted fake model.
* Bhoonidhi LISS-4 and a Mapillary token: 5 m multispectral and street-level facade
  evidence, the two data sources whose absence most limits what the detector can see.
* Replace the keyword-derived `applies_to_change_type` on each clause with a labelled
  pass. It is currently a regex over clause text, and it gates retrieval.
* A corpus-gap report. When retrieval returns nothing, that is a signal about the
  regulation's coverage, and it is currently discarded as an error string.
* A second city, to find out which of the assumptions in §8 were actually assumptions.

**And one thing I would do differently rather than additionally:** the model-facing
contract should have been tested against a real local model on day one. The prompt, the
chunker's identifier scheme and the assess path all passed their unit tests — against a
scripted fake model that returned exactly the ids the tests fed it. Every one of the
three defects fixed this session was invisible to that test suite and obvious within one
real run.
