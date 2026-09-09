"""Temperature scaling fitted on the validation split; expected calibration error."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import numpy as np
import numpy.typing as npt
import torch

TEMPERATURE = Path("data/processed/temperature.json")
Arr = npt.NDArray[np.float64]


def fit_temperature(logits: Arr, labels: Arr) -> float:
    """Minimise NLL of softmax(logits / T) over T on held-out validation data."""
    x = torch.tensor(logits, dtype=torch.float64)
    y = torch.tensor(labels, dtype=torch.long)
    log_t = torch.zeros(1, dtype=torch.float64, requires_grad=True)
    opt = torch.optim.LBFGS([log_t], lr=0.1, max_iter=200)

    def closure() -> torch.Tensor:
        opt.zero_grad()
        loss = torch.nn.functional.cross_entropy(x / log_t.exp(), y)
        loss.backward()  # type: ignore[no-untyped-call]
        return loss

    opt.step(closure)  # type: ignore[no-untyped-call]
    return float(log_t.exp())


def expected_calibration_error(probs: Arr, labels: Arr, bins: int = 10) -> float:
    edges = np.linspace(0, 1, bins + 1)
    ece = 0.0
    for lo, hi in zip(edges[:-1], edges[1:], strict=True):
        m = (probs > lo) & (probs <= hi)
        if m.any():
            ece += m.mean() * abs(probs[m].mean() - labels[m].mean())
    return float(ece)


def save(temperature: float, ece: float, n_val: int) -> None:
    TEMPERATURE.write_text(
        json.dumps(
            {
                "temperature": temperature,
                "ece": ece,
                "n_val": n_val,
                "calibration_date": date.today().isoformat(),
            },
            indent=1,
        )
    )


def load() -> dict[str, object] | None:
    return json.loads(TEMPERATURE.read_text()) if TEMPERATURE.exists() else None
