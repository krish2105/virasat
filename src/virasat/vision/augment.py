"""Flips, 90-degree rotations, small colour jitter. No elastic or perspective warps:
those simulate exactly the misregistration artefact the model must not learn."""

from __future__ import annotations

import torch
from torch import Tensor


def augment_pair(
    before: Tensor, after: Tensor, gen: torch.Generator | None = None
) -> tuple[Tensor, Tensor]:
    k = int(torch.randint(0, 4, (1,), generator=gen))
    before, after = torch.rot90(before, k, (-2, -1)), torch.rot90(after, k, (-2, -1))
    if torch.rand(1, generator=gen) < 0.5:
        before, after = before.flip(-1), after.flip(-1)
    if torch.rand(1, generator=gen) < 0.5:
        before, after = before.flip(-2), after.flip(-2)
    jitter = 1 + (torch.rand(before.shape[0], 1, 1, generator=gen) - 0.5) * 0.1
    return before * jitter, after * jitter
