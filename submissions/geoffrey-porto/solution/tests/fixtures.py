"""Construtores de tabelas sintéticas mínimas para testes unitários.

Cada teste declara só as colunas que importam; o resto vem de DEFAULTS.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

import polars as pl

from churn_diag.loader import CONTRACTS, Tables

DEFAULTS: dict[str, dict[str, Any]] = {
    "accounts": {
        "account_id": "A-1",
        "account_name": "Co",
        "industry": "DevTools",
        "country": "US",
        "signup_date": date(2023, 1, 1),
        "referral_source": "organic",
        "plan_tier": "Pro",
        "seats": 10,
        "is_trial": False,
        "churn_flag": False,
    },
    "subscriptions": {
        "subscription_id": "S-1",
        "account_id": "A-1",
        "start_date": date(2024, 1, 1),
        "end_date": None,
        "plan_tier": "Pro",
        "seats": 10,
        "mrr_amount": 490,
        "arr_amount": 5880,
        "is_trial": False,
        "upgrade_flag": False,
        "downgrade_flag": False,
        "churn_flag": False,
        "billing_frequency": "monthly",
        "auto_renew_flag": True,
    },
    "feature_usage": {
        "usage_id": "U-1",
        "subscription_id": "S-1",
        "usage_date": date(2024, 2, 1),
        "feature_name": "feature_1",
        "usage_count": 5,
        "usage_duration_secs": 100,
        "error_count": 0,
        "is_beta_feature": False,
    },
    "support_tickets": {
        "ticket_id": "T-1",
        "account_id": "A-1",
        "submitted_at": date(2024, 2, 1),
        "closed_at": datetime(2024, 2, 2),
        "resolution_time_hours": 24.0,
        "priority": "low",
        "first_response_time_minutes": 60,
        "satisfaction_score": 4.0,
        "escalation_flag": False,
    },
    "churn_events": {
        "churn_event_id": "C-1",
        "account_id": "A-1",
        "churn_date": date(2024, 6, 1),
        "reason_code": "pricing",
        "refund_amount_usd": 0.0,
        "preceding_upgrade_flag": False,
        "preceding_downgrade_flag": False,
        "is_reactivation": False,
        "feedback_text": None,
    },
}


def frame(name: str, rows: list[dict[str, Any]]) -> pl.DataFrame:
    """DataFrame com o schema do contrato; linhas parciais herdam DEFAULTS."""
    full = [{**DEFAULTS[name], **row} for row in rows]
    return pl.DataFrame(full, schema=CONTRACTS[name], orient="row")


def make_tables(**rows_by_table: list[dict[str, Any]]) -> Tables:
    return Tables(**{n: frame(n, rows_by_table.get(n, [])) for n in CONTRACTS})


def sub(sid: str, start: date, end: date | None = None, **kw: Any) -> dict[str, Any]:
    """Atalho para uma linha de assinatura."""
    return {
        "subscription_id": sid,
        "start_date": start,
        "end_date": end,
        "churn_flag": end is not None,
        **kw,
    }
