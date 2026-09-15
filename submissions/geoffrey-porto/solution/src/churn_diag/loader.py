"""Carga das cinco tabelas com contrato de schema (colunas + tipos)."""

from __future__ import annotations

from dataclasses import dataclass, fields
from pathlib import Path

import polars as pl

CONTRACTS: dict[str, dict[str, pl.DataType]] = {
    "accounts": {
        "account_id": pl.String(),
        "account_name": pl.String(),
        "industry": pl.String(),
        "country": pl.String(),
        "signup_date": pl.Date(),
        "referral_source": pl.String(),
        "plan_tier": pl.String(),
        "seats": pl.Int64(),
        "is_trial": pl.Boolean(),
        "churn_flag": pl.Boolean(),
    },
    "subscriptions": {
        "subscription_id": pl.String(),
        "account_id": pl.String(),
        "start_date": pl.Date(),
        "end_date": pl.Date(),
        "plan_tier": pl.String(),
        "seats": pl.Int64(),
        "mrr_amount": pl.Int64(),
        "arr_amount": pl.Int64(),
        "is_trial": pl.Boolean(),
        "upgrade_flag": pl.Boolean(),
        "downgrade_flag": pl.Boolean(),
        "churn_flag": pl.Boolean(),
        "billing_frequency": pl.String(),
        "auto_renew_flag": pl.Boolean(),
    },
    "feature_usage": {
        "usage_id": pl.String(),
        "subscription_id": pl.String(),
        "usage_date": pl.Date(),
        "feature_name": pl.String(),
        "usage_count": pl.Int64(),
        "usage_duration_secs": pl.Int64(),
        "error_count": pl.Int64(),
        "is_beta_feature": pl.Boolean(),
    },
    "support_tickets": {
        "ticket_id": pl.String(),
        "account_id": pl.String(),
        "submitted_at": pl.Date(),
        "closed_at": pl.Datetime("us"),
        "resolution_time_hours": pl.Float64(),
        "priority": pl.String(),
        "first_response_time_minutes": pl.Int64(),
        "satisfaction_score": pl.Float64(),
        "escalation_flag": pl.Boolean(),
    },
    "churn_events": {
        "churn_event_id": pl.String(),
        "account_id": pl.String(),
        "churn_date": pl.Date(),
        "reason_code": pl.String(),
        "refund_amount_usd": pl.Float64(),
        "preceding_upgrade_flag": pl.Boolean(),
        "preceding_downgrade_flag": pl.Boolean(),
        "is_reactivation": pl.Boolean(),
        "feedback_text": pl.String(),
    },
}


class SchemaContractError(ValueError):
    """Um CSV não respeita o contrato (coluna ausente ou tipo incompatível)."""


@dataclass(frozen=True, slots=True)
class Tables:
    """As cinco tabelas já validadas. Imutável: ninguém altera a fonte."""

    accounts: pl.DataFrame
    subscriptions: pl.DataFrame
    feature_usage: pl.DataFrame
    support_tickets: pl.DataFrame
    churn_events: pl.DataFrame

    def row_counts(self) -> dict[str, int]:
        return {f.name: getattr(self, f.name).height for f in fields(self)}


def enforce_contract(name: str, df: pl.DataFrame) -> pl.DataFrame:
    """Seleciona e tipa as colunas do contrato; falha nomeando tabela e coluna."""
    contract = CONTRACTS[name]
    missing = [col for col in contract if col not in df.columns]
    if missing:
        raise SchemaContractError(f"tabela '{name}': coluna(s) ausente(s) {missing}")
    exprs = []
    for col, dtype in contract.items():
        if df.schema[col] == dtype:
            exprs.append(pl.col(col))
        elif dtype in (pl.Date(), pl.Datetime("us")) and df.schema[col] == pl.String:
            exprs.append(pl.col(col).str.to_datetime(strict=True).cast(dtype))
        else:
            exprs.append(pl.col(col).cast(dtype, strict=True))
    try:
        return df.select(exprs)
    except pl.exceptions.PolarsError as exc:  # pragma: no cover - mensagem
        raise SchemaContractError(
            f"tabela '{name}': tipo incompatível — {exc}"
        ) from exc


def load_tables(data_dir: Path) -> Tables:
    """Lê os cinco CSVs de `data_dir` (somente leitura) e aplica os contratos."""
    frames = {}
    for name in CONTRACTS:
        path = Path(data_dir) / f"ravenstack_{name}.csv"
        raw = pl.read_csv(path, try_parse_dates=True)
        frames[name] = enforce_contract(name, raw)
    return Tables(**frames)
