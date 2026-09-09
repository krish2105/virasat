# VIRASAT — Model card

| Component | Model | Status |
|---|---|---|
| Change detector | Siamese ResNet-50 (timm, ImageNet weights, shared branches), |f(a)−f(b)| → 3×3 conv → BN → ReLU → 1×1 conv, focal loss α=0.25 γ=2 | **Untrained — BLOCKED on 400 tile labels.** Code and shape tests only. |
| Calibration | Temperature scaling fitted on the validation split; ECE reported | BLOCKED (no validation labels). Method verified on synthetic overconfident logits in `tests/unit/test_vision.py`. |
| Facade classifier | ViT-S/16 (timm), 5 classes | BLOCKED (no street imagery). |
| Building-scale candidates | Google Open Buildings 2.5D Temporal presence/height deltas (deterministic adapter) | Live. 103 candidates 2016→2023. Confidence = dataset presence score, uncalibrated. |
| Embeddings | bge-m3 (567M) via Ollama, 1024-d | Live. 178 clauses indexed (pgvector HNSW m=16, ef=64). |
| Reranker | BAAI/bge-reranker-base cross-encoder | Live. |
| Assessor | qwen2.5:14b-instruct (local) / claude-sonnet-5 (cloud), T=0.1 | Live locally. |
| Verifier | llama3.1:8b (local) / claude-opus-5 (cloud), T=0.0 — a different family from the assessor in both modes | Live locally. |

## Evaluation

| Metric | Target | Value |
|---|---|---|
| Detector recall | ≥ 0.85 | BLOCKED — no labels |
| Detector FPR | ≤ 0.15 | BLOCKED |
| ECE | ≤ 0.05 | BLOCKED |
| Facade macro-F1 | ≥ 0.75 | BLOCKED — no street imagery |
| Retrieval precision@3 | ≥ 0.90 | BLOCKED — 0/60 labelled pairs |
| Retrieval recall@5 | ≥ 0.85 | BLOCKED |
| Citation groundedness | ≥ 0.95 | mechanically enforced: a finding citing an unretrieved clause cannot pass the verifier (tested) |
| Verifier catch rate on red-team set | ≥ 0.80 | BLOCKED — measured against the real corpus only once labels exist |
| Per-chowkri FPR disparity | ≤ 1.5 | BLOCKED — < 20 officer decisions per ward |

Spatial splits are enforced in `config/splits.yaml` (held-out chowkris and buffer sectors); the random-vs-spatial ablation will be reported alongside the first trained model.

## Intended use

Drafting assessments for review by a heritage officer of the Jaipur Nagar Nigam / JDA. Not for automatic enforcement, not for any use that identifies an owner or occupant.
