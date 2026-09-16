from __future__ import annotations

from datetime import date

import polars as pl

from churn_diag.account_panel import (
    attach_full_history_rates,
    build_account_panel,
    split_train_test,
)
from churn_diag.features import RATE_FEATURES
from churn_diag.loader import Tables
from churn_diag.screening import (
    age_signal_comparison,
    reference_replication,
    univariate_screening,
)


def test_screening_separates_signal_from_noise() -> None:
    """@spec:AC-020 — AUC e p ajustado por Holm identificam o que tem sinal."""
    n = 400
    y = [1] * (n // 2) + [0] * (n // 2)
    panel = pl.DataFrame(
        {
            "y": y,
            "sinal": [10.0 + i % 3 for i in range(n // 2)]
            + [0.0 + i % 3 for i in range(n // 2)],
            "ruido": [float((i * 37) % 11) for i in range(n)],
        }
    )
    out = univariate_screening(panel, ["sinal", "ruido"])
    row = {r["feature"]: r for r in out.iter_rows(named=True)}
    assert row["sinal"]["auc"] > 0.9
    assert row["sinal"]["significant"]
    assert not row["ruido"]["significant"]
    assert row["ruido"]["p_holm"] >= row["ruido"]["p_value"]
    assert {"n", "n_pos", "direction", "abs_lift"} <= set(out.columns)


def test_rate_features_are_screened_on_both_windows(real_tables: Tables) -> None:
    """@spec:AC-020 — as três taxas medidas em 90 dias e no histórico completo."""
    panel = attach_full_history_rates(real_tables, build_account_panel(real_tables))
    _, test = split_train_test(panel)
    feats = [f"{r}_90d" for r in RATE_FEATURES] + [f"{r}_all" for r in RATE_FEATURES]
    out = univariate_screening(test, feats)
    assert out.height == 6
    assert out["n"].min() > 100
    assert out["p_holm"].is_between(0, 1).all()


def test_reference_replication_reports_roc_and_precision(real_tables: Tables) -> None:
    """@spec:AC-021 — a replicação devolve ROC-AUC e precisão média do teste."""
    panel = build_account_panel(real_tables)
    m = reference_replication(panel)
    assert (m["train_rows"], m["test_rows"]) == (3392, 854)
    assert 0.0 <= m["test_roc_auc"] <= 1.0
    assert 0.0 <= m["test_average_precision"] <= 1.0


def test_identical_ages_are_called_the_same_signal() -> None:
    """@spec:AC-023 — idades idênticas ⇒ veredito "mesmo sinal"."""
    rows = []
    for i in range(300):
        snap = date(2024, 8, 31) if i % 2 else date(2024, 9, 30)
        age = float(i % 150)
        rows.append(
            {
                "snapshot_date": snap,
                "tenure_days": age,
                "min_sub_age_days": age,
                "y": int(age < 40),
            }
        )
    out = age_signal_comparison(pl.DataFrame(rows))
    assert out["spearman_tenure_vs_sub_age"][0] == 1.0
    assert out["ganho_ao_juntar"][0] <= 0.02
    assert out["veredito"][0].startswith("mesmo sinal")
    assert set(out["modelo"]) == {
        "só idade da conta",
        "só idade da assinatura",
        "as duas",
    }


def test_age_comparison_on_real_data_has_verdict(real_tables: Tables) -> None:
    """@spec:AC-023 — no dado real, a comparação sai com correlação e veredito."""
    out = age_signal_comparison(build_account_panel(real_tables))
    assert out["veredito"][0]
    assert -1.0 <= out["spearman_tenure_vs_sub_age"][0] <= 1.0
    assert out["auc_tenure_days"][0] is not None
