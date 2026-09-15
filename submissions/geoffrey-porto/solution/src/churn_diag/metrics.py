"""Métricas de churn: painel assinatura×mês, taxa, risco por idade, padronização.

Unidade de análise = assinatura × mês (tempo discreto). É a única linha do
tempo internamente consistente do dataset (`end_date >= start_date` em 100%).

Duas visões do mesmo painel (DRY):
- `active_at_start`: ativa no 1º dia do mês → taxa mensal clássica de SaaS;
- toda linha ativa em algum momento do mês → risco por idade (inclui quem
  começou e saiu no mesmo mês, justamente o churn de início de vida).
"""

from __future__ import annotations

from datetime import date

import polars as pl
from scipy import stats

from churn_diag.config import (
    AGE_BUCKETS,
    PANEL_START,
    REFERENCE_END,
    REFERENCE_START,
    SNAPSHOT_DATE,
    TARGET_END,
    TARGET_START,
)

PERIOD_ORDER = ("pre", "reference", "target")


def age_bucket_expr(col: str = "age_days") -> pl.Expr:
    """Expressão Polars que mapeia idade em dias para a faixa de AGE_BUCKETS."""
    expr = None
    for label, lo, hi in AGE_BUCKETS:
        cond = pl.col(col) >= lo if hi is None else pl.col(col).is_between(lo, hi - 1)
        expr = (pl.when(cond) if expr is None else expr.when(cond)).then(pl.lit(label))
    return expr.otherwise(None).alias("age_bucket")


def period_expr(col: str = "month") -> pl.Expr:
    return (
        pl.when(pl.col(col).is_between(TARGET_START, TARGET_END))
        .then(pl.lit("target"))
        .when(pl.col(col).is_between(REFERENCE_START, REFERENCE_END))
        .then(pl.lit("reference"))
        .otherwise(pl.lit("pre"))
        .alias("period")
    )


def exposure_panel(
    subs: pl.DataFrame, start: date = PANEL_START, end: date = SNAPSHOT_DATE
) -> pl.DataFrame:
    """Uma linha por assinatura por mês em que ela esteve ativa."""
    months = pl.DataFrame({"month": pl.date_range(start, end, "1mo", eager=True)})
    next_month = pl.col("month").dt.offset_by("1mo")
    return (
        subs.join(months, how="cross")
        .filter(
            pl.col("start_date") < next_month,
            pl.col("end_date").is_null() | (pl.col("end_date") >= pl.col("month")),
        )
        .with_columns(
            age_days=pl.max_horizontal(
                (pl.col("month") - pl.col("start_date")).dt.total_days(), pl.lit(0)
            ),
            active_at_start=pl.col("start_date") <= pl.col("month"),
            ended=pl.col("end_date").is_not_null() & (pl.col("end_date") < next_month),
            paid_mrr=pl.when(pl.col("is_trial"))
            .then(0)
            .otherwise(pl.col("mrr_amount")),
        )
        .with_columns(age_bucket_expr(), period_expr())
        .sort("month", "subscription_id")
    )


def monthly_churn(panel: pl.DataFrame) -> pl.DataFrame:
    """Taxa mensal: encerradas no mês ÷ ativas no 1º dia (contagem e MRR pago)."""
    bom = panel.filter(pl.col("active_at_start"))
    rates = bom.group_by("month").agg(
        active_subs=pl.len(),
        churned_subs=pl.col("ended").sum(),
        active_mrr=pl.col("paid_mrr").sum(),
        churned_mrr=pl.col("paid_mrr").filter(pl.col("ended")).sum(),
    )
    counts = panel.group_by("month").agg(
        ended_all=pl.col("ended").sum(),
        mrr_ended_all=pl.col("paid_mrr").filter(pl.col("ended")).sum(),
    )
    return (
        rates.join(counts, on="month", how="full", coalesce=True)
        .fill_null(0)
        .with_columns(
            sub_churn_rate=(pl.col("churned_subs") / pl.col("active_subs")).fill_nan(0),
            mrr_churn_rate=(pl.col("churned_mrr") / pl.col("active_mrr")).fill_nan(0),
        )
        .with_columns(pl.col("sub_churn_rate", "mrr_churn_rate").round(5))
        .with_columns(period_expr())
        .sort("month")
    )


def hazard_table(panel: pl.DataFrame, by: list[str]) -> pl.DataFrame:
    """Risco mensal (eventos ÷ exposições) e risco em MRR por grupo."""
    return (
        panel.group_by(by)
        .agg(
            exposures=pl.len(),
            events=pl.col("ended").sum(),
            mrr_exposed=pl.col("paid_mrr").sum(),
            mrr_lost=pl.col("paid_mrr").filter(pl.col("ended")).sum(),
        )
        .with_columns(
            hazard=(pl.col("events") / pl.col("exposures")).round(5),
            mrr_hazard=(pl.col("mrr_lost") / pl.col("mrr_exposed"))
            .fill_nan(0)
            .round(5),
        )
        .sort(by)
    )


def standardized_ratio(
    panel: pl.DataFrame,
    reference: str = "reference",
    target: str = "target",
    by: str = "age_bucket",
) -> dict[str, float]:
    """Observado vs esperado no alvo, aplicando o risco de referência por faixa.

    Razão ≈ 1 → a mudança é só de mix; razão > 1 → o risco por faixa piorou.
    O p-valor é o teste exato de Poisson (observado ≥ esperado).
    """
    ref = hazard_table(panel.filter(pl.col("period") == reference), [by])
    tgt = hazard_table(panel.filter(pl.col("period") == target), [by])
    joined = tgt.join(
        ref.select(
            by, pl.col("hazard").alias("h_ref"), pl.col("mrr_hazard").alias("r_ref")
        ),
        on=by,
        how="left",
    ).fill_null(0)
    observed = int(joined["events"].sum())
    expected = float((joined["exposures"] * joined["h_ref"]).sum())
    mrr_obs = float(joined["mrr_lost"].sum())
    mrr_exp = float((joined["mrr_exposed"] * joined["r_ref"]).sum())
    p = (
        float(stats.poisson.sf(observed - 1, expected))
        if expected > 0
        else float("nan")
    )
    return {
        "observed": observed,
        "expected": round(expected, 1),
        "ratio": round(observed / expected, 2) if expected else float("nan"),
        "p_value": p,
        "mrr_observed": round(mrr_obs, 0),
        "mrr_expected": round(mrr_exp, 0),
        "mrr_ratio": round(mrr_obs / mrr_exp, 2) if mrr_exp else float("nan"),
    }


def control_flags(
    series: pl.DataFrame, value_col: str, reference_mask: pl.Expr, k: float = 3.0
) -> pl.DataFrame:
    """Marca pontos acima de média + k·σ do período de referência (quebra)."""
    ref = series.filter(reference_mask)[value_col]
    mean, sd = float(ref.mean()), float(ref.std())
    ucl = mean + k * sd
    return series.with_columns(
        ref_mean=pl.lit(round(mean, 5)),
        ucl=pl.lit(round(ucl, 5)),
        is_break=pl.col(value_col) > ucl,
    )
