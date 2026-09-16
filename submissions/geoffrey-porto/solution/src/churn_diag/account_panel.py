"""Painel conta × snapshot mensal — replica o desenho da referência.

Desenho lido em `docs/referencia/screen_ravenstack_features.py`:
conta num fim de mês, features olhando 90 dias para trás, rótulo = evento de
churn não-reativação nos 30 dias seguintes, treino até 31/08/2024.

Duas diferenças declaradas:
1. As features usam eventos **estritamente anteriores** ao corte (a referência
   inclui o próprio dia do snapshot) — permite o teste de vazamento do AC-022.
2. `upgrade_share`, `downgrade_share` e `auto_renew_share` não entram: são
   flags sem data (P-009, quarentena em `features.QUARANTINED_UNDATED`).
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Final

import polars as pl

from churn_diag.features import (
    DERIVED_FEATURES,
    TIMELINE_UNRELIABLE,
    attach_derived_features,
    rate_features,
    ticket_rates,
    timeline_features,
    usage_rates,
    zscore_stats,
)
from churn_diag.loader import Tables

SNAPSHOT_FIRST: Final[date] = date(2023, 4, 30)
SNAPSHOT_LAST: Final[date] = date(2024, 10, 31)
WINDOW_DAYS: Final[int] = 90
HORIZON_DAYS: Final[int] = 30
TRAIN_THROUGH: Final[date] = date(2024, 8, 31)

ACCOUNT_NUMERIC: Final[tuple[str, ...]] = (
    "tenure_days",
    "active_mrr",
    "active_seats",
    "active_subscriptions",
    "annual_share",
    "min_sub_age_days",
    "mean_sub_age_days",
    "usage_total_90d",
    "usage_duration_90d",
    "feature_breadth_90d",
    "beta_usage_share_90d",
    "errors_per_100_uses_90d",
    "tickets_90d",
    "escalation_rate_90d",
    "resolution_time_mean_90d",
    "response_time_p90_90d",
    "high_priority_ticket_share_90d",
    "satisfaction_mean_90d",
    "satisfaction_missing_share_90d",
    "seats",
    "is_trial",
)
ACCOUNT_CATEGORICAL: Final[tuple[str, ...]] = (
    "plan_tier",
    "industry",
    "country",
    "referral_source",
)


def month_end_snapshots(
    first: date = SNAPSHOT_FIRST, last: date = SNAPSHOT_LAST
) -> list[date]:
    """Fins de mês entre `first` e `last` (inclusive)."""
    months = pl.date_range(first.replace(day=1), last.replace(day=1), "1mo", eager=True)
    ends = [(m + timedelta(days=32)).replace(day=1) - timedelta(days=1) for m in months]
    return [d for d in ends if first <= d <= last]


def _commercial(subs: pl.DataFrame, t0: date) -> pl.DataFrame:
    active = subs.filter(
        pl.col("start_date") <= t0,
        pl.col("end_date").is_null() | (pl.col("end_date") >= t0),
    ).with_columns(age=(pl.lit(t0) - pl.col("start_date")).dt.total_days())
    return active.group_by("account_id").agg(
        active_mrr=pl.col("mrr_amount").sum(),
        active_seats=pl.col("seats").sum(),
        active_subscriptions=pl.col("subscription_id").n_unique(),
        annual_share=(pl.col("billing_frequency") == "annual").mean(),
        min_sub_age_days=pl.col("age").min(),
        mean_sub_age_days=pl.col("age").mean(),
    )


def _usage_window(t: Tables, t0: date) -> pl.DataFrame:
    usage = t.feature_usage.filter(
        pl.col("usage_date") < t0,
        pl.col("usage_date") >= t0 - timedelta(days=WINDOW_DAYS),
    ).join(
        t.subscriptions.select("subscription_id", "account_id"),
        on="subscription_id",
        how="inner",
    )
    agg = usage.group_by("account_id").agg(
        usage_total_90d=pl.col("usage_count").sum(),
        usage_duration_90d=pl.col("usage_duration_secs").sum(),
        feature_breadth_90d=pl.col("feature_name").n_unique(),
        beta_usage_share_90d=pl.col("is_beta_feature").mean(),
    )
    rates = usage_rates(t, t0, WINDOW_DAYS).select(
        "account_id", errors_per_100_uses_90d=pl.col("errors_per_100_uses")
    )
    return agg.join(rates, on="account_id", how="left")


def _tickets_window(t: Tables, t0: date) -> pl.DataFrame:
    tickets = t.support_tickets.filter(
        pl.col("submitted_at") < t0,
        pl.col("submitted_at") >= t0 - timedelta(days=WINDOW_DAYS),
    )
    agg = tickets.group_by("account_id").agg(
        resolution_time_mean_90d=pl.col("resolution_time_hours").mean(),
        response_time_p90_90d=pl.col("first_response_time_minutes").quantile(0.90),
        high_priority_ticket_share_90d=pl.col("priority")
        .is_in(["high", "urgent"])
        .mean(),
        satisfaction_mean_90d=pl.col("satisfaction_score").mean(),
    )
    rates = ticket_rates(t, t0, WINDOW_DAYS).select(
        "account_id",
        tickets_90d=pl.col("tickets_n"),
        escalation_rate_90d=pl.col("escalation_rate"),
        satisfaction_missing_share_90d=pl.col("satisfaction_missing_share"),
    )
    return rates.join(agg, on="account_id", how="left")


def _label(t: Tables, t0: date, horizon_days: int) -> pl.DataFrame:
    end = t0 + timedelta(days=horizon_days)
    return (
        t.churn_events.filter(
            pl.col("churn_date") > t0,
            pl.col("churn_date") <= end,
            ~pl.col("is_reactivation"),
        )
        .select("account_id")
        .unique()
        .with_columns(y=pl.lit(1, dtype=pl.Int8))
    )


def build_account_panel(
    t: Tables,
    snapshots: list[date] | None = None,
    horizon_days: int = HORIZON_DAYS,
) -> pl.DataFrame:
    """Uma linha por conta com assinatura ativa em cada fim de mês."""
    frames = []
    accounts = t.accounts.select(
        "account_id",
        "industry",
        "country",
        "referral_source",
        "plan_tier",
        "seats",
        pl.col("is_trial").cast(pl.Int8),
        "signup_date",
    )
    for t0 in snapshots if snapshots is not None else month_end_snapshots():
        commercial = _commercial(t.subscriptions, t0)
        if commercial.is_empty():
            continue
        frame = (
            accounts.join(commercial, on="account_id", how="inner")
            .join(_usage_window(t, t0), on="account_id", how="left")
            .join(_tickets_window(t, t0), on="account_id", how="left")
            .join(_label(t, t0, horizon_days), on="account_id", how="left")
            .with_columns(
                snapshot_date=pl.lit(t0),
                tenure_days=(pl.lit(t0) - pl.col("signup_date")).dt.total_days(),
                y=pl.col("y").fill_null(0),
            )
            .drop("signup_date")
        )
        frames.append(frame)
    panel = pl.concat(frames, how="vertical_relaxed")
    return panel.select(
        "account_id",
        "snapshot_date",
        "y",
        *ACCOUNT_NUMERIC,
        *ACCOUNT_CATEGORICAL,
    ).sort("snapshot_date", "account_id")


def split_train_test(
    panel: pl.DataFrame, train_through: date = TRAIN_THROUGH
) -> tuple[pl.DataFrame, pl.DataFrame]:
    """Mesmo corte da referência: treino até 31/08/2024, teste depois."""
    return (
        panel.filter(pl.col("snapshot_date") <= train_through),
        panel.filter(pl.col("snapshot_date") > train_through),
    )


def attach_derived(panel: pl.DataFrame) -> pl.DataFrame:
    """Acrescenta as derivadas da referência, com z-scores ajustados no treino.

    As derivadas **não** entram em `ACCOUNT_NUMERIC`: a replicação do desenho da
    referência reproduz a lista publicada, que não as inclui.
    """
    train, _ = split_train_test(panel)
    return attach_derived_features(panel, zscore_stats(train))


def attach_full_history_rates(t: Tables, panel: pl.DataFrame) -> pl.DataFrame:
    """Acrescenta as taxas calculadas sobre todo o histórico (sufixo `_all`).

    Serve para separar "a taxa não tem sinal" de "a janela de 90 dias mede datas
    desalinhadas" (ASM-008).
    """
    frames = []
    for t0 in panel["snapshot_date"].unique().sort().to_list():
        rates = rate_features(t, t0, window_days=None).select(
            "account_id",
            errors_per_100_uses_all=pl.col("errors_per_100_uses"),
            escalation_rate_all=pl.col("escalation_rate"),
            satisfaction_missing_share_all=pl.col("satisfaction_missing_share"),
        )
        frames.append(rates.with_columns(snapshot_date=pl.lit(t0)))
    return panel.join(
        pl.concat(frames, how="vertical_relaxed"),
        on=["account_id", "snapshot_date"],
        how="left",
    )


DERIVED_COLUMNS: Final[tuple[str, ...]] = DERIVED_FEATURES


TIMELINE_COLUMNS: Final[tuple[str, ...]] = tuple(
    f"{name}{suffix}"
    for name in TIMELINE_UNRELIABLE
    for suffix in ("_bruto", "_consistente")
)


def attach_timeline_features(t: Tables, panel: pl.DataFrame) -> pl.DataFrame:
    """Anexa tendência e recência de uso nos dois recortes, para MEDIÇÃO.

    Ficam fora de `ACCOUNT_NUMERIC` de propósito: não entram na replicação da
    referência nem no score de produção (AC-032).
    """
    frames = []
    for t0 in panel["snapshot_date"].unique().sort().to_list():
        bruto = timeline_features(t, t0)
        consistente = timeline_features(t, t0, consistent=True)
        frames.append(
            bruto.join(
                consistente, on="account_id", how="full", coalesce=True
            ).with_columns(snapshot_date=pl.lit(t0))
        )
    return panel.join(
        pl.concat(frames, how="diagonal_relaxed"),
        on=["account_id", "snapshot_date"],
        how="left",
    )
