"""Tile-pair dataset over data/processed. Labels come only from data/processed/labels.jsonl."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import torch
from torch import Tensor
from torch.utils.data import Dataset

PROCESSED = Path("data/processed")
LABELS = PROCESSED / "labels.jsonl"


def load_labels() -> dict[str, int]:
    if not LABELS.exists():
        return {}
    rows = [json.loads(ln) for ln in LABELS.read_text().splitlines() if ln.strip()]
    return {r["tile_id"]: int(r["change"]) for r in rows}


def norm_stats() -> tuple[Tensor, Tensor]:
    stats = json.loads((PROCESSED / "norm_stats.json").read_text())
    mean = torch.tensor(stats["mean"], dtype=torch.float32).view(-1, 1, 1)
    std = torch.tensor(stats["std"], dtype=torch.float32).view(-1, 1, 1)
    return mean, std


class TilePairs(Dataset[tuple[Tensor, Tensor, Tensor, str]]):
    def __init__(self, split: str, labelled_only: bool = True) -> None:
        index = [json.loads(ln) for ln in (PROCESSED / "index.jsonl").read_text().splitlines()]
        labels = load_labels()
        self.items = [
            m
            for m in index
            if m["split"] == split
            and not m["quarantined"]
            and (not labelled_only or m["tile_id"] in labels)
        ]
        self.labels = labels
        self.mean, self.std = norm_stats()

    def __len__(self) -> int:
        return len(self.items)

    def __getitem__(self, i: int) -> tuple[Tensor, Tensor, Tensor, str]:
        m = self.items[i]
        npz = np.load(PROCESSED / "tiles" / f"{m['tile_id']}.npz")
        before = (torch.from_numpy(npz["before"]).float() - self.mean) / self.std
        after = (torch.from_numpy(npz["after"]).float() - self.mean) / self.std
        label = torch.tensor(self.labels.get(m["tile_id"], -1))
        return before, after, label, m["tile_id"]
