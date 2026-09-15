"""Orquestra o diagnóstico e grava `outputs/` de forma determinística.

`metrics.json` tem duas seções:
- `report`: chaves planas citadas no RELATORIO.md (conferidas pelo teste P-003);
- `quality`: a auditoria completa de qualidade de dados.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import polars as pl

from churn_diag import figures
from churn_diag.config import AGE_BUCKETS, CONTROL_SIGMA, YOUNG_AGE_DAYS, Settings
from churn_diag.hypotheses import Context, findings_frame, invariance_table, run_all
from churn_diag.impact import ab_test_design, excess_mrr, recovery_scenarios
from churn_diag.loader import Tables, load_tables
from churn_diag.metrics import (
    control_flags,
    exposure_panel,
    hazard_table,
    monthly_churn,
    standardized_ratio,
)
from churn_diag.quality import (
    cohort_churn_profile,
    duration_to_window_ratio,
    quality_report,
)
from churn_diag.risk import (
    cs_priority_list,
    monthly_hazard_by_age,
    oot_validation,
    subscription_risk,
)

AGE_ORDER = [b[0] for b in AGE_BUCKETS]


@dataclass(frozen=True, slots=True)
class Result:
    report: dict[str, float | int]
    quality: dict[str, object]
    tables: dict[str, pl.DataFrame]


def _pct(x: float, nd: int = 1) -> float:
    return round(100 * float(x), nd)


def _k(x: float) -> float:
    return round(float(x) / 1000, 0)


def _period_mean(monthly: pl.DataFrame, col: str, period: str) -> float:
    return float(monthly.filter(pl.col("period") == period)[col].mean())


def _month(monthly: pl.DataFrame, col: str, month: str) -> float:
    return float(monthly.filter(pl.col("month") == pl.lit(month).str.to_date())[col][0])


def _hz(hz: pl.DataFrame, period: str, bucket: str) -> float:
    return float(
        hz.filter(pl.col("period") == period, pl.col("age_bucket") == bucket)["hazard"][
            0
        ]
    )


def _env(inv: pl.DataFrame, env: str, col: str, nd: int) -> float:
    return round(float(inv.filter(pl.col("env") == env)[col][0]), nd)


def _starts(t: Tables, start: str, end: str) -> int:
    d = pl.col("start_date")
    lo, hi = pl.lit(start).str.to_date(), pl.lit(end).str.to_date()
    return t.subscriptions.filter(d.is_between(lo, hi)).height


def analyse(t: Tables, cs_top_n: int) -> Result:
    """Roda todo o diagnóstico em memória (sem I/O) — fácil de testar."""
    quality = quality_report(t)
    panel = exposure_panel(t.subscriptions)
    monthly = monthly_churn(panel)
    m24 = monthly.filter(pl.col("month") >= pl.date(2024, 1, 1))
    ctrl = control_flags(
        m24, "mrr_churn_rate", pl.col("period") == "reference", CONTROL_SIGMA
    )
    hz = hazard_table(panel.filter(pl.col("period") != "pre"), ["period", "age_bucket"])
    std = standardized_ratio(panel)
    oot = oot_validation(t)
    findings = run_all(Context(t, panel, oot))
    ff = findings_frame(findings)
    inv = invariance_table(t, panel)
    cross = inv.filter(pl.col("env_type") != "periodo")  # indústria, plano, canal
    sub_risk = subscription_risk(t, monthly_hazard_by_age(panel))
    cs = cs_priority_list(t, sub_risk, cs_top_n)
    exc = excess_mrr(panel)
    rec = recovery_scenarios(exc["excess_mrr_per_month"])
    ab = ab_test_design(panel)
    cohorts = cohort_churn_profile(t)

    young_mask = pl.col("age_days") < YOUNG_AGE_DAYS
    tgt = panel.filter(pl.col("period") == "target")
    ref = panel.filter(pl.col("period") == "reference")

    def hz_mask(p: pl.DataFrame, mask: pl.Expr) -> float:
        return float(p.filter(mask)["ended"].mean())

    usage = (
        t.feature_usage.filter(pl.col("usage_date").dt.year() == 2024)
        .group_by(pl.col("usage_date").dt.truncate("1mo").alias("month"))
        .agg(usage=pl.col("usage_count").sum())
        .join(m24.select("month", "active_subs"), on="month")
        .sort("month")
    )
    usage_idx = usage.with_columns(
        usage_idx=(100 * pl.col("usage") / pl.col("usage").first()).round(1),
        active_idx=(100 * pl.col("active_subs") / pl.col("active_subs").first()).round(
            1
        ),
    )
    f = {r["id"]: r for r in ff.iter_rows(named=True)}
    o = {r["scorer"]: r for r in oot.iter_rows(named=True)}
    cq = {r["cohort"].isoformat(): r for r in cohorts.iter_rows(named=True)}
    tl, cd = quality["timeline"], quality["churn_definitions"]
    csat_2024 = t.support_tickets.filter(pl.col("submitted_at").dt.year() == 2024)

    report: dict[str, float | int] = {
        # dados e qualidade
        "n_accounts": t.accounts.height,
        "n_subscriptions": t.subscriptions.height,
        "n_usage_events": t.feature_usage.height,
        "n_tickets": t.support_tickets.height,
        "n_churn_events": t.churn_events.height,
        "usage_before_sub_start_pct": tl["usage_before_sub_start_pct"],
        "usage_before_signup_pct": tl["usage_before_signup_pct"],
        "tickets_before_signup_pct": tl["tickets_before_signup_pct"],
        "churn_events_before_first_sub": tl["churn_events_before_first_sub"],
        "churn_def_flag_account": cd["flag_account"],
        "churn_def_events": cd["has_churn_event"],
        "churn_def_sub_ended": cd["has_ended_subscription"],
        "churn_def_disagree": cd["disagree"],
        "churn_def_disagree_pct": _pct(cd["disagree"] / cd["accounts"]),
        "churn_def_event_but_flag_false": cd["event_but_flag_false"],
        "usage_id_collisions": quality["usage_id_collisions"],
        "reason_feedback_cramers_v": quality["reason_vs_feedback"]["cramers_v"],
        "reason_share_min_pct": quality["reason_vs_feedback"]["reason_share_min_pct"],
        "reason_share_max_pct": quality["reason_vs_feedback"]["reason_share_max_pct"],
        "csat_missing_pct": quality["satisfaction_missing_pct"],
        "cohort_2023q4_ever_ended_pct": cq["2023-10-01"]["ever_ended_pct"],
        "cohort_2023q4_days_observed": int(cq["2023-10-01"]["days_observed"]),
        "cohort_2024q4_ever_ended_pct": cq["2024-10-01"]["ever_ended_pct"],
        "cohort_2024q4_days_observed": int(cq["2024-10-01"]["days_observed"]),
        "duration_ratio_median": duration_to_window_ratio(t),
        # tendência
        "active_subs_jan24": int(_month(monthly, "active_subs", "2024-01-01")),
        "active_subs_dec24": int(_month(monthly, "active_subs", "2024-12-01")),
        "active_subs_growth_x": round(
            _month(monthly, "active_subs", "2024-12-01")
            / _month(monthly, "active_subs", "2024-01-01"),
            1,
        ),
        "ended_subs_dec24": int(_month(monthly, "ended_all", "2024-12-01")),
        "starts_q3_24": _starts(t, "2024-07-01", "2024-09-30"),
        "starts_q4_24": _starts(t, "2024-10-01", "2024-12-31"),
        "ended_subs_ref_avg": round(_period_mean(monthly, "ended_all", "reference"), 1),
        "mrr_churn_ref_avg_pct": _pct(
            _period_mean(monthly, "mrr_churn_rate", "reference"), 2
        ),
        "mrr_churn_oct24_pct": _pct(_month(monthly, "mrr_churn_rate", "2024-10-01"), 2),
        "mrr_churn_nov24_pct": _pct(_month(monthly, "mrr_churn_rate", "2024-11-01"), 2),
        "mrr_churn_dec24_pct": _pct(_month(monthly, "mrr_churn_rate", "2024-12-01"), 2),
        "sub_churn_ref_avg_pct": _pct(
            _period_mean(monthly, "sub_churn_rate", "reference"), 2
        ),
        "sub_churn_dec24_pct": _pct(_month(monthly, "sub_churn_rate", "2024-12-01"), 2),
        "control_ucl_pct": _pct(float(ctrl["ucl"][0]), 2),
        "control_breaks": int(ctrl["is_break"].sum()),
        "q4_observed_ended": std["observed"],
        "q4_expected_ended": std["expected"],
        "q4_ratio_x": std["ratio"],
        "q4_mrr_lost_k": _k(std["mrr_observed"]),
        "q4_mrr_expected_k": _k(std["mrr_expected"]),
        "q4_mrr_ratio_x": std["mrr_ratio"],
        "hz_0_30_ref_pct": _pct(_hz(hz, "reference", "0-30d"), 2),
        "hz_0_30_target_pct": _pct(_hz(hz, "target", "0-30d"), 2),
        "hz_0_30_mult_x": round(
            _hz(hz, "target", "0-30d") / _hz(hz, "reference", "0-30d"), 1
        ),
        "hz_30_90_ref_pct": _pct(_hz(hz, "reference", "30-90d"), 2),
        "hz_30_90_target_pct": _pct(_hz(hz, "target", "30-90d"), 2),
        "hz_mature_ref_pct": _pct(hz_mask(ref, ~young_mask), 2),
        "hz_mature_target_pct": _pct(hz_mask(tgt, ~young_mask), 2),
        "young_share_q4_events_pct": _pct(
            tgt.filter(young_mask)["ended"].sum() / tgt["ended"].sum()
        ),
        # contradições do CEO
        "csat_mean_2024": round(float(csat_2024["satisfaction_score"].mean()), 2),
        "csat_auc": round(f["H3"]["effect"], 2),
        "usage_change_per_sub_pct": _pct(f["H4"]["effect"]),
        "usage_monthly_min": int(usage["usage"].min()),
        "usage_monthly_max": int(usage["usage"].max()),
        "usage_trend_p": round(f["H4"]["p_value"], 2),
        "support_reason_auc": round(f["H6"]["effect"], 2),
        "rr_young_x": round(
            float(f["H2"]["detail"].split("RR jovem ")[1].split("×")[0]), 2
        ),
        "rr_mature_x": round(
            float(f["H2"]["detail"].split("RR madura ")[1].split("×")[0]), 2
        ),
        "h8_rho": round(f["H8"]["effect"], 2),
        "h8_p": round(f["H8"]["p_value"], 3),
        "h8_p_holm": round(f["H8"]["p_holm"], 2),
        "segments_min_p_holm": round(
            min(f[h]["p_holm"] for h in ("H9", "H10", "H11", "H12")), 2
        ),
        "n_hypotheses": len(findings),
        "n_significant": int(ff["significant"].sum()),
        # previsão
        "oot_base_rate_pct": _pct(o["gbm_todas_tabelas"]["base_rate"]),
        "oot_n_test": int(o["gbm_todas_tabelas"]["n_test"]),
        "oot_positives": round(
            o["gbm_todas_tabelas"]["n_test"] * o["gbm_todas_tabelas"]["base_rate"]
        ),
        "oot_age_roc": round(o["idade_da_assinatura"]["roc_auc"], 2),
        "oot_age_p": round(o["idade_da_assinatura"]["p_value"], 3),
        "oot_gbm_roc": round(o["gbm_todas_tabelas"]["roc_auc"], 2),
        "oot_gbm_insample_roc": round(o["gbm_todas_tabelas"]["roc_auc_in_sample"], 2),
        "oot_logit_roc": round(o["logistica_todas_tabelas"]["roc_auc"], 2),
        "oot_mrr_only_roc": round(o["so_mrr"]["roc_auc"], 2),
        "oot_expected_loss_mrr_recall_pct": _pct(
            o["perda_esperada_mrr"]["mrr_recall_at_10"]
        ),
        "oot_mrr_only_mrr_recall_pct": _pct(o["so_mrr"]["mrr_recall_at_10"]),
        "oot_gbm_mrr_recall_pct": _pct(o["gbm_todas_tabelas"]["mrr_recall_at_10"]),
        "invariance_envs": cross.height,
        "invariance_positive": int((cross["direction"] == "+").sum()),
        "invariance_ci_excludes_1": int(cross["ci_excludes_1"].sum()),
        "invariance_hr_min_x": round(float(cross["hr"].min()), 1),
        "invariance_hr_max_x": round(float(cross["hr"].max()), 1),
        "hr_before_break_x": _env(inv, "antes (jan-set/24)", "hr", 1),
        "hr_before_ci_low": _env(inv, "antes (jan-set/24)", "ci_low", 2),
        "hr_before_ci_high": _env(inv, "antes (jan-set/24)", "ci_high", 2),
        "hr_after_break_x": _env(inv, "depois (out-dez/24)", "hr", 1),
        "hr_after_ci_low": _env(inv, "depois (out-dez/24)", "ci_low", 2),
        "hr_after_ci_high": _env(inv, "depois (out-dez/24)", "ci_high", 2),
        # risco e impacto
        "paid_mrr_active_k": _k(sub_risk["paid_mrr"].sum()),
        "expected_loss_90d_k": _k(sub_risk["expected_loss"].sum()),
        "expected_loss_90d_pct": _pct(
            sub_risk["expected_loss"].sum() / sub_risk["paid_mrr"].sum()
        ),
        "cs_top_n": cs.height,
        "cs_top_expected_loss_k": _k(cs["expected_loss_90d"].sum()),
        "cs_top_share_of_loss_pct": _pct(
            cs["expected_loss_90d"].sum() / sub_risk["expected_loss"].sum()
        ),
        "cs_top_active_mrr_k": _k(cs["active_paid_mrr"].sum()),
        "excess_mrr_q4_k": _k(exc["excess_mrr_target"]),
        "excess_mrr_per_month_k": _k(exc["excess_mrr_per_month"]),
        "recovery_25_mrr_month_k": _k(rec["25pct"]["mrr_per_month"]),
        "recovery_50_mrr_month_k": _k(rec["50pct"]["mrr_per_month"]),
        "recovery_75_mrr_month_k": _k(rec["75pct"]["mrr_per_month"]),
        "recovery_50_arr_equiv_k": _k(rec["50pct"]["arr_equivalent"]),
        "ab_p0_pct": _pct(ab["p0_first_30d"], 2),
        "ab_p1_pct": _pct(ab["p1_target"], 2),
        "ab_n_per_arm": ab["n_per_arm"],
        "ab_new_paid_subs_month": int(ab["new_paid_subs_per_month"]),
        "ab_weeks_to_enroll": ab["weeks_to_enroll"],
    }
    report = {
        k: (v.item() if isinstance(v, np.generic) else v) for k, v in report.items()
    }
    out_tables = {
        "monthly_churn": monthly,
        "control_chart_2024": ctrl,
        "hazard_by_age": hz,
        "findings": ff,
        "invariance": inv,
        "oot_validation": oot,
        "cs_priority_accounts": cs,
        "cohort_churn_profile": cohorts,
        "usage_vs_base_2024": usage_idx,
    }
    return Result(report=report, quality=quality, tables=out_tables)


def write_outputs(result: Result, out_dir: Path) -> list[Path]:
    """Grava JSON/CSVs (determinísticos) e figuras."""
    out_dir.mkdir(parents=True, exist_ok=True)
    fig_dir = out_dir / "figures"
    fig_dir.mkdir(exist_ok=True)
    payload = {"report": result.report, "quality": result.quality}
    metrics = out_dir / "metrics.json"
    metrics.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False, default=str)
        + "\n",
        encoding="utf-8",
    )
    written = [metrics]
    for name, df in result.tables.items():
        path = out_dir / f"{name}.csv"
        df.write_csv(path, float_precision=6)
        written.append(path)
    tb = result.tables
    q = result.quality["timeline"]
    written += [
        figures.churn_count_vs_rate(
            tb["monthly_churn"],
            float(tb["control_chart_2024"]["ucl"][0]),
            fig_dir / "01_contagem_vs_taxa.png",
        ),
        figures.hazard_by_age(
            tb["hazard_by_age"], AGE_ORDER, fig_dir / "02_risco_por_idade.png"
        ),
        figures.usage_vs_base(tb["usage_vs_base_2024"], fig_dir / "03_uso_vs_base.png"),
        figures.data_quality(
            [
                ("uso antes da assinatura existir", q["usage_before_sub_start_pct"]),
                ("tickets antes do cadastro da conta", q["tickets_before_signup_pct"]),
                (
                    "contas com definições de churn em conflito",
                    result.report["churn_def_disagree_pct"],
                ),
                ("tickets sem nota de satisfação", result.report["csat_missing_pct"]),
            ],
            fig_dir / "04_qualidade_dos_dados.png",
        ),
        figures.oot_models(
            tb["oot_validation"], fig_dir / "05_validacao_fora_do_tempo.png"
        ),
    ]
    return written


def run(settings: Settings) -> Result:
    tables = load_tables(settings.data_dir)
    result = analyse(tables, settings.cs_top_n)
    write_outputs(result, settings.out_dir)
    return result
