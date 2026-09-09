import json
from pathlib import Path

import numpy as np
import pytest

from virasat.ingest import street


def test_writer_refuses_unblurred_array(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(street, "OUT", tmp_path)
    raw = np.zeros((64, 64, 3), dtype=np.uint8)
    with pytest.raises(TypeError):
        street.write(raw, "x", {})  # type: ignore[arg-type]
    assert not list(tmp_path.iterdir())


def test_blur_returns_image_and_sidecar_records_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(street, "OUT", tmp_path)
    img = np.full((64, 64, 3), 127, dtype=np.uint8)
    path = street.write(street.blur(img), "y", {"source": "test"})
    assert path.exists()
    assert json.loads((tmp_path / "y.json").read_text())["blur_applied"] is True


def test_no_unblurred_image_in_processed() -> None:
    """Every street image on disk must carry a sidecar proving the blur ran."""
    out = Path("data/processed/street")
    if not out.exists():
        pytest.skip("no street imagery ingested yet")
    for jpg in out.glob("*.jpg"):
        side = jpg.with_suffix(".json")
        assert side.exists() and json.loads(side.read_text())["blur_applied"] is True, jpg
