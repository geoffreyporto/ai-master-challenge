from __future__ import annotations

import hashlib
from pathlib import Path

from churn_diag.config import Settings, resolve_data_dir
from churn_diag.pipeline import run


def _digest(folder: Path) -> dict[str, str]:
    files = sorted([folder / "metrics.json", *folder.glob("*.csv")])
    return {f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in files}


def test_two_runs_are_byte_identical(tmp_path: Path) -> None:
    """@spec:AC-017 @principle:P-006 — duas execuções, mesmos bytes em JSON e CSVs."""
    data = resolve_data_dir()
    run(Settings(data, tmp_path / "a"))
    run(Settings(data, tmp_path / "b"))
    a, b = _digest(tmp_path / "a"), _digest(tmp_path / "b")
    assert len(a) >= 8
    assert a == b
