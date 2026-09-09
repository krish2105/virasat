"""Train the Siamese detector on the spatial split, calibrate on val, report on test.

Refuses to run without owner labels (data/processed/labels.jsonl). Seeds, git SHA and
config hash are logged; checkpoints carry their metrics in the filename.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import subprocess
from pathlib import Path

import numpy as np
import structlog
import torch
from torch import Tensor
from torch.utils.data import DataLoader

from virasat.vision.augment import augment_pair
from virasat.vision.calibrate import expected_calibration_error, fit_temperature, save
from virasat.vision.data import TilePairs, load_labels
from virasat.vision.siamese import FocalLoss, SiameseChangeNet, tile_probability

log = structlog.get_logger()
CKPT = Path("data/processed/checkpoints")
MIN_LABELS = 100


def seed_all(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def evaluate(
    model: SiameseChangeNet,
    loader: DataLoader[tuple[Tensor, Tensor, Tensor, str]],
    device: torch.device,
) -> tuple[np.ndarray, np.ndarray]:  # type: ignore[type-arg]
    model.eval()
    logits, labels = [], []
    with torch.no_grad():
        for b, a, y, _ in loader:
            out = model(b.to(device), a.to(device))
            p = tile_probability(out)
            logits.append(torch.stack([torch.log1p(-p + 1e-6), torch.log(p + 1e-6)], dim=1).cpu())
            labels.append(y)
    return torch.cat(logits).numpy(), torch.cat(labels).numpy()


def metrics(probs: np.ndarray, labels: np.ndarray, threshold: float = 0.5) -> dict[str, float]:  # type: ignore[type-arg]
    pred = probs >= threshold
    pos, neg = labels == 1, labels == 0
    recall = float(pred[pos].mean()) if pos.any() else float("nan")
    fpr = float(pred[neg].mean()) if neg.any() else float("nan")
    return {"recall": recall, "fpr": fpr, "n": int(len(labels))}


def main() -> None:
    parser = argparse.ArgumentParser(prog="train")
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--lr", type=float, default=3e-4)
    args = parser.parse_args()

    labels = load_labels()
    if len(labels) < MIN_LABELS:
        raise SystemExit(
            f"train: BLOCKED — {len(labels)}/{MIN_LABELS} labelled tiles (run `uv run label-tiles`)"
        )
    seed_all(args.seed)
    device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    sha = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip()
    config_hash = hashlib.sha256(json.dumps(vars(args), sort_keys=True).encode()).hexdigest()[:8]
    log.info(
        "train_start", seed=args.seed, git_sha=sha, config_hash=config_hash, device=str(device)
    )

    train, val, test = (TilePairs(s) for s in ("train", "val", "test"))
    if len(train) == 0 or len(val) == 0:
        raise SystemExit("train: BLOCKED — empty train or val split after labelling")
    model = SiameseChangeNet().to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr)
    loss_fn = FocalLoss()
    gen = torch.Generator().manual_seed(args.seed)
    loader = DataLoader(train, batch_size=16, shuffle=True)
    for epoch in range(args.epochs):
        model.train()
        total = 0.0
        for b, a, y, _ in loader:
            b, a = augment_pair(b, a, gen)
            target = y.view(-1, 1, 1).expand(-1, b.shape[-2], b.shape[-1]).to(device)
            loss = loss_fn(model(b.to(device), a.to(device)), target)
            opt.zero_grad()
            loss.backward()
            opt.step()
            total += float(loss)
        log.info("epoch", epoch=epoch, loss=round(total / max(1, len(loader)), 4))

    val_logits, val_labels = evaluate(model, DataLoader(val, batch_size=32), device)
    temperature = fit_temperature(val_logits.astype(np.float64), val_labels.astype(np.float64))
    val_probs = torch.softmax(torch.tensor(val_logits) / temperature, dim=1)[:, 1].numpy()
    ece = expected_calibration_error(val_probs, val_labels)
    save(temperature, ece, len(val))

    test_logits, test_labels = evaluate(model, DataLoader(test, batch_size=32), device)
    test_probs = torch.softmax(torch.tensor(test_logits) / temperature, dim=1)[:, 1].numpy()
    m = metrics(test_probs, test_labels)
    CKPT.mkdir(parents=True, exist_ok=True)
    name = f"siamese_{sha}_{config_hash}_recall{m['recall']:.2f}_fpr{m['fpr']:.2f}_ece{ece:.3f}.pt"
    torch.save(
        {
            "state_dict": model.state_dict(),
            "temperature": temperature,
            "seed": args.seed,
            "git_sha": sha,
            "config": vars(args),
            "test_metrics": m,
            "ece": ece,
        },
        CKPT / name,
    )
    log.info(
        "train_done", checkpoint=name, test=m, ece=round(ece, 4), temperature=round(temperature, 3)
    )


if __name__ == "__main__":
    main()
