from __future__ import annotations

import shutil
from pathlib import Path

import polars as pl
import pytest

from churn_diag.config import resolve_data_dir
from churn_diag.loader import CONTRACTS, SchemaContractError, Tables, load_tables


def test_real_tables_match_contract_and_counts(real_tables: Tables) -> None:
    """@spec:AC-001 — as cinco tabelas carregam com contrato e contagens."""
    assert real_tables.row_counts() == {
        "accounts": 500,
        "subscriptions": 5000,
        "feature_usage": 25000,
        "support_tickets": 2000,
        "churn_events": 600,
    }
    for name, contract in CONTRACTS.items():
        df: pl.DataFrame = getattr(real_tables, name)
        assert dict(df.schema) == contract, name


def test_missing_column_names_table_and_column(tmp_path: Path) -> None:
    """@spec:AC-001 — coluna ausente interrompe com tabela e coluna na mensagem."""
    src = resolve_data_dir()
    for csv in src.glob("ravenstack_*.csv"):
        shutil.copy(csv, tmp_path / csv.name)
    broken = tmp_path / "ravenstack_subscriptions.csv"
    pl.read_csv(broken).drop("mrr_amount").write_csv(broken)

    with pytest.raises(SchemaContractError, match=r"subscriptions.*mrr_amount"):
        load_tables(tmp_path)
