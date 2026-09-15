"""Configuração central: caminhos, semente e constantes de negócio.

Tudo que é "número mágico" do diagnóstico mora aqui, com o porquê ao lado.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Final

SEED: Final[int] = 42

DATA_ENV_VAR: Final[str] = "RAVENSTACK_DATA_DIR"
SOLUTION_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
# Caminho padrão dentro do fork do desafio; alternativa: solution/data/ (gitignored).
REPO_DATASET_DIR: Final[Path] = (
    SOLUTION_ROOT.parents[2] / "challenges" / "data-001-churn" / "dataset"
)
LOCAL_DATASET_DIR: Final[Path] = SOLUTION_ROOT / "data"
DEFAULT_OUT_DIR: Final[Path] = SOLUTION_ROOT / "outputs"

# Último dia observado em todas as tabelas (ASM-002).
SNAPSHOT_DATE: Final[date] = date(2024, 12, 31)

# Períodos de comparação: referência = 1º–3º tri/2024; alvo = 4º tri/2024.
REFERENCE_START: Final[date] = date(2024, 1, 1)
REFERENCE_END: Final[date] = date(2024, 9, 30)
TARGET_START: Final[date] = date(2024, 10, 1)
TARGET_END: Final[date] = date(2024, 12, 31)
PANEL_START: Final[date] = date(2023, 1, 1)

# Faixas de idade da assinatura em dias: (rótulo, início inclusivo, fim exclusivo).
AGE_BUCKETS: Final[tuple[tuple[str, int, int | None], ...]] = (
    ("0-30d", 0, 30),
    ("30-90d", 30, 90),
    ("90-180d", 90, 180),
    ("180-365d", 180, 365),
    ("365d+", 365, None),
)
YOUNG_AGE_DAYS: Final[int] = 90  # "assinatura jovem" para o CS

# Validação fora do tempo: treina com o corte de jul, testa com o corte de out.
OOT_TRAIN_T0: Final[date] = date(2024, 7, 1)
OOT_TEST_T0: Final[date] = date(2024, 10, 1)
OOT_HORIZON_DAYS: Final[int] = 92
TOP_FRACTION: Final[float] = 0.10  # capacidade do CS: 10% da carteira por ciclo

RISK_HORIZON_MONTHS: Final[int] = 3
CS_TOP_N: Final[int] = 50
RECOVERY_SCENARIOS: Final[tuple[float, ...]] = (0.25, 0.50, 0.75)
CONTROL_SIGMA: Final[float] = 3.0


class DataDirNotFoundError(FileNotFoundError):
    """Os CSVs não foram encontrados em nenhum dos caminhos conhecidos."""


def resolve_data_dir(explicit: str | Path | None = None) -> Path:
    """Resolve o diretório dos CSVs: argumento > variável de ambiente > padrões."""
    candidates: list[Path] = []
    if explicit:
        candidates.append(Path(explicit))
    if env := os.environ.get(DATA_ENV_VAR):
        candidates.append(Path(env))
    candidates += [LOCAL_DATASET_DIR, REPO_DATASET_DIR]
    for path in candidates:
        if (path / "ravenstack_accounts.csv").is_file():
            return path.resolve()
    tried = "\n  ".join(str(p) for p in candidates)
    raise DataDirNotFoundError(
        "CSVs da RavenStack não encontrados. Baixe o dataset do Kaggle "
        "(rivalytics/saas-subscription-and-churn-analytics-dataset) e aponte "
        f"{DATA_ENV_VAR} para a pasta. Caminhos tentados:\n  {tried}"
    )


@dataclass(frozen=True, slots=True)
class Settings:
    """Parâmetros de uma execução do pipeline (imutável)."""

    data_dir: Path
    out_dir: Path = DEFAULT_OUT_DIR
    cs_top_n: int = CS_TOP_N
