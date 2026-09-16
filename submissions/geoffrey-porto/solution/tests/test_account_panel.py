from __future__ import annotations

from datetime import date

import polars as pl

from churn_diag.account_panel import (
    ACCOUNT_CATEGORICAL,
    ACCOUNT_NUMERIC,
    build_account_panel,
    month_end_snapshots,
    split_train_test,
)
from churn_diag.features import QUARANTINED_UNDATED
from churn_diag.loader import Tables

# Números publicados pela triagem de referência (docs/referencia/).
REF_TRAIN_ROWS, REF_TRAIN_POS = 3392, 0.0693
REF_TEST_ROWS, REF_TEST_POS = 854, 0.1066


def test_panel_reproduces_the_reference_design(real_tables: Tables) -> None:
    """@spec:AC-021 — conta × fim de mês, mesmo recorte e mesmas taxas de evento."""
    snaps = month_end_snapshots()
    assert snaps[0] == date(2023, 4, 30)
    assert snaps[-1] == date(2024, 10, 31)

    panel = build_account_panel(real_tables)
    train, test = split_train_test(panel)
    assert (train.height, test.height) == (REF_TRAIN_ROWS, REF_TEST_ROWS)
    assert round(float(train["y"].mean()), 4) == REF_TRAIN_POS
    assert round(float(test["y"].mean()), 4) == REF_TEST_POS
    assert set(ACCOUNT_NUMERIC) | set(ACCOUNT_CATEGORICAL) <= set(panel.columns)


def test_label_uses_only_non_reactivation_events_after_the_cutoff(
    real_tables: Tables,
) -> None:
    """@spec:AC-021 — o rótulo é evento de churn não-reativação nos 30 dias seguintes."""
    t0 = date(2024, 6, 30)
    panel = build_account_panel(real_tables, snapshots=[t0])
    expected = (
        real_tables.churn_events.filter(
            pl.col("churn_date") > t0,
            pl.col("churn_date") <= date(2024, 7, 30),
            ~pl.col("is_reactivation"),
        )["account_id"]
        .unique()
        .to_list()
    )
    flagged = panel.filter(pl.col("y") == 1)["account_id"].to_list()
    assert set(flagged) <= set(expected)  # só contas com assinatura ativa entram
    assert flagged


def test_account_panel_never_sees_the_future(real_tables: Tables) -> None:
    """@spec:AC-022 — apagar uso e tickets a partir do corte não muda nenhuma feature."""
    t0 = date(2024, 6, 30)
    full = build_account_panel(real_tables, snapshots=[t0])
    past_only = Tables(
        accounts=real_tables.accounts,
        subscriptions=real_tables.subscriptions,
        feature_usage=real_tables.feature_usage.filter(pl.col("usage_date") < t0),
        support_tickets=real_tables.support_tickets.filter(pl.col("submitted_at") < t0),
        churn_events=real_tables.churn_events,  # o rótulo precisa do futuro
    )
    cut = build_account_panel(past_only, snapshots=[t0])
    features = [*ACCOUNT_NUMERIC, *ACCOUNT_CATEGORICAL]
    assert full.select(features).equals(cut.select(features))


def test_quarantined_flags_are_absent(real_tables: Tables) -> None:
    """@spec:AC-024 @principle:P-009 — nenhuma flag sem data no painel por conta."""
    panel = build_account_panel(real_tables, snapshots=[date(2024, 6, 30)])
    for flag in QUARANTINED_UNDATED:
        assert not any(flag in c for c in panel.columns), flag
