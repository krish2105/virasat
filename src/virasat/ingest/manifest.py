"""Every file under data/ is recorded in data/MANIFEST.md. Unrecorded data does not exist."""

from __future__ import annotations

import hashlib
from datetime import date
from pathlib import Path

MANIFEST = Path("data/MANIFEST.md")
_PLACEHOLDER = "| _(none yet)_ |"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def record(
    path: Path, *, source: str, licence: str, extent: str, crs: str, notes: str = ""
) -> None:
    """Append (or replace) the manifest row for `path`."""
    rel = path.as_posix()
    row = (
        f"| `{rel}` | {source} | {licence} | {date.today().isoformat()} | {extent} | {crs} "
        f"| `{sha256(path)}` | {notes} |"
    )
    lines = MANIFEST.read_text().splitlines()
    lines = [ln for ln in lines if not ln.startswith((_PLACEHOLDER, f"| `{rel}` |"))]
    if not any(ln.startswith("| File |") for ln in lines):
        raise RuntimeError("MANIFEST.md has no table header")
    header = next(i for i, ln in enumerate(lines) if ln.startswith("| File |"))
    if "| Notes |" not in lines[header]:
        lines[header] = lines[header].rstrip() + " Notes |"
        lines[header + 1] = lines[header + 1].rstrip() + "---|"
    lines.append(row)
    MANIFEST.write_text("\n".join(lines) + "\n")
