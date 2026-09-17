"""Primeira execução em ambiente novo (ex.: Streamlit Community Cloud).

Só constrói o índice de similares (`build_serving`): o modelo servido, as
métricas e os resultados do Pioneer já vêm versionados.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from support_redesign.config import OUTPUTS_DIR

MODELS = OUTPUTS_DIR / "models"
REQUIRED: tuple[Path, ...] = (
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
        from support_redesign.pipeline import build_serving

        runner = build_serving
    runner()
    return True
