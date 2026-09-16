from __future__ import annotations

from datetime import date

import polars as pl
import pytest
from fixtures import make_tables, sub

from churn_diag.features import QUARANTINED_UNDATED
from churn_diag.loader import Tables
from churn_diag.risk import (
    CAT_FEATURES,
    NUMERIC_FEATURES,
    build_oot_panel,
    cs_priority_list,
    design_matrix,
    oot_validation,
    subscription_risk,
)

HAZARDS = {
    "0-30d": 0.10,
    "30-90d": 0.05,
    "90-180d": 0.02,
    "180-365d": 0.01,
    "365d+": 0.01,
}


def test_expected_loss_is_hazard_times_paid_mrr() -> None:
    """@spec:AC-012 — perda = risco × MRR das pagas; trial contribui zero."""
    t = make_tables(
        accounts=[{"account_id": "A-1"}],
        subscriptions=[
            sub("S-1", date(2024, 12, 21), None, mrr_amount=1000),  # 10 dias
            sub("S-2", date(2023, 1, 1), None, mrr_amount=500),  # 365d+
            sub("S-3", date(2024, 12, 21), None, mrr_amount=0, is_trial=True),
        ],
    )
    r = subscription_risk(t, HAZARDS, asof=date(2024, 12, 31), horizon_months=1)
    loss = dict(zip(r["subscription_id"], r["expected_loss"], strict=True))
    assert loss["S-1"] == pytest.approx(100.0)
    assert loss["S-2"] == pytest.approx(5.0)
    assert loss["S-3"] == 0.0


def test_risk_ages_the_subscription_month_by_month() -> None:
    """@spec:AC-012 — em 3 meses, a assinatura muda de faixa e o risco acompanha."""
    t = make_tables(
        subscriptions=[sub("S-1", date(2024, 12, 21), None, mrr_amount=1000)]
    )
    r = subscription_risk(t, HAZARDS, asof=date(2024, 12, 31), horizon_months=3)
    expected = 1 - (1 - 0.10) * (1 - 0.05) * (1 - 0.05)  # 10d, 40d, 70d
    assert r["p_churn"][0] == pytest.approx(expected, abs=1e-5)


def test_cs_list_is_sorted_and_actionable() -> None:
    """@spec:AC-013 — colunas acionáveis, ordem decrescente de perda esperada."""
    t = make_tables(
        accounts=[
            {"account_id": "A-1", "account_name": "Alfa"},
            {"account_id": "A-2", "account_name": "Beta"},
        ],
        subscriptions=[
            sub("S-1", date(2024, 12, 1), None, account_id="A-1", mrr_amount=100),
            sub("S-2", date(2024, 12, 1), None, account_id="A-2", mrr_amount=5000),
        ],
    )
    cs = cs_priority_list(t, subscription_risk(t, HAZARDS), top_n=10)
    assert cs["account_id"].to_list() == ["A-2", "A-1"]
    for col in (
        "account_name",
        "active_paid_mrr",
        "expected_loss_90d",
        "young_subs",
        "motivo",
        "acao_sugerida",
    ):
        assert col in cs.columns
    assert cs["expected_loss_90d"].is_sorted(descending=True)
    assert cs["acao_sugerida"].str.len_chars().min() > 10


def test_oot_panel_never_sees_the_future(real_tables: Tables) -> None:
    """@spec:AC-014 @principle:P-002 — apagar tudo que é ≥ T0 não muda nenhuma variável."""
    t0 = date(2024, 7, 1)
    full = build_oot_panel(real_tables, t0)
    past_only = Tables(
        accounts=real_tables.accounts,
        subscriptions=real_tables.subscriptions,  # o rótulo precisa do futuro
        feature_usage=real_tables.feature_usage.filter(pl.col("usage_date") < t0),
        support_tickets=real_tables.support_tickets.filter(pl.col("submitted_at") < t0),
        churn_events=real_tables.churn_events.filter(pl.col("churn_date") < t0),
    )
    cut = build_oot_panel(past_only, t0)
    features = [*NUMERIC_FEATURES, *CAT_FEATURES]
    assert full.select(features).equals(cut.select(features))
    assert "churn_flag" not in full.columns
    assert "end_date" not in full.columns


def test_oot_report_has_business_metrics(real_tables: Tables) -> None:
    """@spec:AC-014 — ROC-AUC, PR-AUC, lift@10% e recall de MRR@10% por score."""
    oot = oot_validation(real_tables)
    assert {"roc_auc", "pr_auc", "lift_at_10", "mrr_recall_at_10"} <= set(oot.columns)
    assert {"idade_da_assinatura", "gbm_todas_tabelas", "so_mrr"} <= set(oot["scorer"])
    assert oot["roc_auc"].is_between(0, 1).all()


def test_diagnosis_panel_has_no_undated_flags(real_tables: Tables) -> None:
    """@spec:AC-024 @principle:P-009 — flags sem data fora da matriz do diagnóstico."""
    panel = build_oot_panel(real_tables, date(2024, 7, 1))
    _, categories = design_matrix(panel)
    columns = set(panel.columns) | {
        f"{c}={v}" for c, vs in categories.items() for v in vs
    }
    for flag in QUARANTINED_UNDATED:
        assert not any(flag in c for c in columns), flag
