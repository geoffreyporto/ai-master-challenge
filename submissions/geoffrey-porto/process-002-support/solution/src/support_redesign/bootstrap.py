"""Primeira execução em ambiente novo (ex.: Streamlit Community Cloud)."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from support_redesign.config import OUTPUTS_DIR

MODELS = OUTPUTS_DIR / "models"
REQUIRED: tuple[Path, ...] = (
    OUTPUTS_DIR / "metrics.json",
    OUTPUTS_DIR / "d2_test.parquet",
    OUTPUTS_DIR / "d1_scored.parquet",
    MODELS / "b0.pkl",
    MODELS / "index_embeddings.npy",
    MODELS / "index_rows.parquet",
)


def artifacts_ready(required: tuple[Path, ...] = REQUIRED) -> bool:
    return all(p.is_file() for p in required)


def ensure_artifacts(
    runner: Callable[[], object] | None = None, required: tuple[Path, ...] = REQUIRED
) -> bool:
    """Roda o pipeline só se faltar artefato. Devolve True se rodou."""
    if artifacts_ready(required):
        return False
    if runner is None:
        from support_redesign.pipeline import run

        runner = run
    runner()
    return True
