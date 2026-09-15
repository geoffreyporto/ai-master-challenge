"""Auditoria de qualidade: duplicatas, linha do tempo e definições de churn.

Pergunta que este módulo responde para o CEO: "posso confiar nesses números?".
"""

from __future__ import annotations

from datetime import date

import numpy as np
import polars as pl
from scipy import stats

from churn_diag.config import SNAPSHOT_DATE
from churn_diag.loader import Tables


def dedupe_exact(df: pl.DataFrame) -> tuple[pl.DataFrame, int]:
    """Remove só linhas 100% idênticas (ordem estável). Devolve (df, removidas)."""
    out = df.unique(maintain_order=True)
    return out, df.height - out.height


def id_collisions(df: pl.DataFrame, id_col: str) -> int:
    """IDs repetidos com conteúdo diferente — colisões, não duplicatas."""
    distinct = df.unique()
    return int(distinct.filter(pl.col(id_col).is_duplicated())[id_col].n_unique())


def timeline_violations(t: Tables) -> dict[str, float]:
    """Eventos cujas datas contradizem o ciclo de vida do cliente."""
    usage = t.feature_usage.join(
        t.subscriptions.select(
            "subscription_id", "account_id", "start_date", "end_date"
        ),
        on="subscription_id",
        how="inner",
    ).join(t.accounts.select("account_id", "signup_date"), on="account_id", how="inner")
    before_start = usage.filter(pl.col("usage_date") < pl.col("start_date")).height
    after_end = usage.filter(
        pl.col("end_date").is_not_null() & (pl.col("usage_date") > pl.col("end_date"))
    ).height
    before_signup_usage = usage.filter(
        pl.col("usage_date") < pl.col("signup_date")
    ).height

    tickets = t.support_tickets.join(
        t.accounts.select("account_id", "signup_date"), on="account_id", how="inner"
    )
    tickets_before = tickets.filter(
        pl.col("submitted_at") < pl.col("signup_date")
    ).height

    first_sub = t.subscriptions.group_by("account_id").agg(
        pl.col("start_date").min().alias("first_start")
    )
    churn = t.churn_events.join(first_sub, on="account_id", how="inner")
    churn_before = churn.filter(pl.col("churn_date") < pl.col("first_start")).height

    subs = t.subscriptions.join(
        t.accounts.select("account_id", "signup_date"), on="account_id", how="inner"
    )
    subs_before = subs.filter(pl.col("start_date") < pl.col("signup_date")).height
    bad_end = t.subscriptions.filter(pl.col("end_date") < pl.col("start_date")).height

    n_usage, n_tickets = max(usage.height, 1), max(tickets.height, 1)
    return {
        "usage_before_sub_start": before_start,
        "usage_before_sub_start_pct": round(100 * before_start / n_usage, 1),
        "usage_after_sub_end": after_end,
        "usage_before_signup_pct": round(100 * before_signup_usage / n_usage, 1),
        "tickets_before_signup": tickets_before,
        "tickets_before_signup_pct": round(100 * tickets_before / n_tickets, 1),
        "churn_events_before_first_sub": churn_before,
        "subs_before_signup": subs_before,
        "subs_end_before_start": bad_end,
    }


def churn_definitions(t: Tables) -> pl.DataFrame:
    """Uma linha por conta com as três definições de churn do dataset."""
    event_ids = t.churn_events.select("account_id").unique()
    ended = (
        t.subscriptions.filter(pl.col("end_date").is_not_null())
        .select("account_id")
        .unique()
    )
    return (
        t.accounts.select("account_id", pl.col("churn_flag").alias("def_account_flag"))
        .join(
            event_ids.with_columns(pl.lit(True).alias("def_churn_event")),
            on="account_id",
            how="left",
        )
        .join(
            ended.with_columns(pl.lit(True).alias("def_sub_ended")),
            on="account_id",
            how="left",
        )
        .fill_null(False)
        .sort("account_id")
    )


def churn_definition_agreement(t: Tables) -> dict[str, int]:
    """Quantas contas cada definição marca e em quantas elas discordam."""
    d = churn_definitions(t)
    cols = ["def_account_flag", "def_churn_event", "def_sub_ended"]
    n_true = d.select(pl.sum_horizontal(cols).alias("n"))["n"]
    return {
        "accounts": d.height,
        "flag_account": int(d["def_account_flag"].sum()),
        "has_churn_event": int(d["def_churn_event"].sum()),
        "has_ended_subscription": int(d["def_sub_ended"].sum()),
        "all_three_agree_churn": int((n_true == 3).sum()),
        "all_three_agree_active": int((n_true == 0).sum()),
        "disagree": int(((n_true > 0) & (n_true < 3)).sum()),
        "event_but_flag_false": int(
            d.filter(pl.col("def_churn_event") & ~pl.col("def_account_flag")).height
        ),
        "flag_true_without_event": int(
            d.filter(pl.col("def_account_flag") & ~pl.col("def_churn_event")).height
        ),
    }


def cramers_v(table: np.ndarray) -> tuple[float, float, float]:
    """(qui-quadrado, p-valor, V de Cramér) de uma tabela de contingência."""
    chi2, p, _, _ = stats.chi2_contingency(table)
    v = float(np.sqrt(chi2 / (table.sum() * (min(table.shape) - 1))))
    return float(chi2), float(p), v


def reason_feedback_consistency(t: Tables) -> dict[str, float]:
    """O motivo codificado concorda com o texto livre? (V≈0 = não concorda)."""
    tab = (
        t.churn_events.drop_nulls("feedback_text")
        .group_by("reason_code", "feedback_text")
        .len()
        .pivot(on="feedback_text", index="reason_code", values="len")
        .fill_null(0)
        .sort("reason_code")
    )
    chi2, p, v = cramers_v(tab.drop("reason_code").to_numpy())
    shares = t.churn_events["reason_code"].value_counts(normalize=True)["proportion"]
    return {
        "chi2": round(chi2, 2),
        "p_value": round(p, 3),
        "cramers_v": round(v, 3),
        "reason_share_max_pct": round(100 * float(shares.max()), 1),
        "reason_share_min_pct": round(100 * float(shares.min()), 1),
        "feedback_missing_pct": round(
            100 * t.churn_events["feedback_text"].null_count() / t.churn_events.height,
            1,
        ),
    }


def cohort_churn_profile(t: Tables, snapshot: date = SNAPSHOT_DATE) -> pl.DataFrame:
    """Fração de assinaturas que 'já saíram' por trimestre de início.

    Em SaaS real, coortes mais antigas acumulam MAIS churn (tiveram mais tempo).
    Se a fração é a mesma para coorte de 1 mês e de 20 meses, o `end_date`
    provavelmente é atribuído, não observado — alerta para o CEO (ASM-003).
    """
    return (
        t.subscriptions.with_columns(
            cohort=pl.col("start_date").dt.truncate("1q"),
            days_observed=(pl.lit(snapshot) - pl.col("start_date")).dt.total_days(),
        )
        .group_by("cohort")
        .agg(
            subs=pl.len(),
            ever_ended_pct=(100 * pl.col("end_date").is_not_null().mean()).round(1),
            days_observed=pl.col("days_observed").mean().round(0),
        )
        .sort("cohort")
    )


def duration_to_window_ratio(t: Tables, snapshot: date = SNAPSHOT_DATE) -> float:
    """Mediana de (duração até sair ÷ tempo observado). Uniforme ⇒ ~0,5."""
    ended = t.subscriptions.filter(pl.col("end_date").is_not_null()).with_columns(
        ratio=(pl.col("end_date") - pl.col("start_date")).dt.total_days()
        / (pl.lit(snapshot) - pl.col("start_date")).dt.total_days()
    )
    return round(float(ended["ratio"].fill_nan(None).drop_nulls().median()), 2)


def quality_report(t: Tables) -> dict[str, object]:
    """Consolida a auditoria num dicionário serializável (vai para metrics.json)."""
    _, usage_exact_dups = dedupe_exact(t.feature_usage)
    return {
        "row_counts": t.row_counts(),
        "usage_exact_duplicates": usage_exact_dups,
        "usage_id_collisions": id_collisions(t.feature_usage, "usage_id"),
        "timeline": timeline_violations(t),
        "churn_definitions": churn_definition_agreement(t),
        "reason_vs_feedback": reason_feedback_consistency(t),
        "satisfaction_missing_pct": round(
            100
            * t.support_tickets["satisfaction_score"].null_count()
            / t.support_tickets.height,
            1,
        ),
    }
