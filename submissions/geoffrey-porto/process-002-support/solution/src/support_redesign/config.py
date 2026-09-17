"""Configuração única do projeto: caminhos, semente e parâmetros de decisão."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Final

SEED: Final[int] = 42

SOLUTION_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
DATA_DIR: Final[Path] = SOLUTION_ROOT / "data"
OUTPUTS_DIR: Final[Path] = SOLUTION_ROOT / "outputs"
ASSUMPTIONS_FILE: Final[Path] = SOLUTION_ROOT / "assumptions.yaml"
README_FILE: Final[Path] = SOLUTION_ROOT.parent / "README.md"

D1_FILE: Final[str] = "customer_support_tickets.csv"
D2_FILE: Final[str] = "all_tickets_processed_improved_v3.csv"

TOPICS: Final[tuple[str, ...]] = (
    "Access",
    "Administrative rights",
    "HR Support",
    "Hardware",
    "Internal Project",
    "Miscellaneous",
    "Purchase",
    "Storage",
)

SPLIT_FRACTIONS: Final[tuple[float, float, float]] = (0.70, 0.10, 0.20)

TARGET_PRECISION: Final[float] = 0.95  # ASM-004 / Q-002
CONFORMAL_ALPHA: Final[float] = 0.05
OOD_QUANTILE: Final[float] = 0.02  # fração do validação abaixo do guarda de domínio
HUMAN_ONLY_TOPICS: Final[frozenset[str]] = frozenset({"Miscellaneous"})  # ASM-005
CONFIRM_PRIORITIES: Final[frozenset[str]] = frozenset({"Critical"})
MAX_TEXT_CHARS: Final[int] = 20_000

MODEL2VEC_NAME: Final[str] = "minishlab/potion-base-8M"
PIONEER_CLASSIFIER: Final[str] = "fastino/gliner2-multi-large-v1"
PIONEER_CLASSIFIER_FALLBACK: Final[str] = "fastino/gliner2-large-v1"
PIONEER_GUARDRAIL: Final[str] = "fastino/gliguard-PII-multi"
PIONEER_LLM: Final[str] = "deepseek-ai/DeepSeek-V4-Flash"
PIONEER_PRIVACY: Final[str] = "fastino/gliner2-privacy-filter-PII-multi"
PII_LABELS: Final[tuple[str, ...]] = (
    "person",
    "email",
    "phone number",
    "street address",
    "credit card number",
)
PII_MIN_CONFIDENCE: Final[float] = 0.5
LLM_SAMPLE_PER_CLASS: Final[int] = 50
PII_SAMPLE_SIZE: Final[int] = 200
DRAFT_SAMPLE_SIZE: Final[int] = 30
RECALL_KS: Final[tuple[int, ...]] = (1, 5, 10)
N_HUMAN_EXAMPLES: Final[int] = 8


class DataDirNotFoundError(FileNotFoundError):
    """Os CSVs não estão onde o pipeline espera."""


def resolve_data_dir() -> Path:
    data_dir = Path(os.environ.get("SUPPORT_DATA_DIR", DATA_DIR))
    missing = [f for f in (D1_FILE, D2_FILE) if not (data_dir / f).is_file()]
    if missing:
        raise DataDirNotFoundError(
            f"Faltam {missing} em {data_dir}. Baixe com: kaggle datasets download "
            "-d suraj520/customer-support-ticket-dataset e "
            "-d adisongoh/it-service-ticket-classification-dataset --unzip -p data/"
        )
    return data_dir
