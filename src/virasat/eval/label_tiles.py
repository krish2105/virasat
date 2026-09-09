"""`uv run label-tiles` — the owner labels tile pairs as change / no-change.

Shows before/after side by side (matplotlib-free: writes a PNG and opens it), then
asks c / n / s(kip) / q. Stratified: cycles through spatial blocks so every chowkri
and sector gets labels. Appends to data/processed/labels.jsonl.
"""

from __future__ import annotations

import json
import subprocess
import sys
from itertools import cycle
from pathlib import Path

import numpy as np
from PIL import Image

from virasat.vision.data import LABELS, PROCESSED, load_labels

PREVIEW = Path("data/interim/label_preview.png")


def _rgb(arr: np.ndarray) -> np.ndarray:  # type: ignore[type-arg]
    rgb = np.stack([arr[2], arr[1], arr[0]], -1).astype(float)
    lo, hi = np.percentile(rgb, 2), np.percentile(rgb, 98)
    out: np.ndarray = (np.clip((rgb - lo) / max(hi - lo, 1), 0, 1) * 255).astype(np.uint8)  # type: ignore[type-arg]
    return out


def main() -> None:
    index = [json.loads(ln) for ln in (PROCESSED / "index.jsonl").read_text().splitlines()]
    done = load_labels()
    blocks: dict[str, list[dict[str, object]]] = {}
    for m in index:
        if not m["quarantined"] and m["tile_id"] not in done:
            blocks.setdefault(m["spatial_block"], []).append(m)
    order = cycle(sorted(blocks))
    remaining = sum(len(v) for v in blocks.values())
    print(f"{len(done)} labelled, {remaining} remaining; c=change n=no-change s=skip q=quit")
    PREVIEW.parent.mkdir(parents=True, exist_ok=True)
    while blocks:
        block = next(order)
        if not blocks.get(block):
            blocks.pop(block, None)
            continue
        m = blocks[block].pop(0)
        npz = np.load(PROCESSED / "tiles" / f"{m['tile_id']}.npz")
        pair = np.concatenate(
            [
                _rgb(npz["before"]),
                np.full((npz["before"].shape[1], 4, 3), 255, np.uint8),
                _rgb(npz["after"]),
            ],
            axis=1,
        )
        Image.fromarray(pair).resize(
            (pair.shape[1] * 12, pair.shape[0] * 12), Image.Resampling.NEAREST
        ).save(PREVIEW)
        subprocess.Popen(["open", str(PREVIEW)]) if sys.platform == "darwin" else None
        ans = (
            input(f"[{block}] {m['tile_id']} {m['epoch_before']}->{m['epoch_after']}> ")
            .strip()
            .lower()
        )
        if ans == "q":
            break
        if ans in ("c", "n"):
            with LABELS.open("a") as f:
                f.write(
                    json.dumps(
                        {"tile_id": m["tile_id"], "change": int(ans == "c"), "spatial_block": block}
                    )
                    + "\n"
                )


if __name__ == "__main__":
    main()
