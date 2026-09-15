from __future__ import annotations

import polars as pl
import pytest

from churn_diag.impact import ab_sample_size, excess_mrr, recovery_scenarios


def test_excess_mrr_and_scenarios_in_dollars_per_month() -> None:
    """@spec:AC-015 — excesso sobre o esperado e cenários de 25/50/75% em $/mês."""
    rows = []
    for period, bucket, n, events in [
        ("reference", "novo", 100, 1),
        ("reference", "maduro", 100, 1),
        ("target", "novo", 100, 7),
        ("target", "maduro", 100, 1),
    ]:
        rows += [
            {
                "period": period,
                "age_bucket": bucket,
                "ended": i < events,
                "paid_mrr": 1000,
            }
            for i in range(n)
        ]
    exc = excess_mrr(pl.DataFrame(rows), months_in_target=3)
    assert exc["mrr_lost_target"] == 8000
    assert exc["mrr_expected_target"] == 2000
    assert exc["excess_mrr_target"] == 6000
    assert exc["excess_mrr_per_month"] == 2000
    rec = recovery_scenarios(exc["excess_mrr_per_month"])
    assert {k: v["mrr_per_month"] for k, v in rec.items()} == {
        "25pct": 500,
        "50pct": 1000,
        "75pct": 1500,
    }
    assert rec["50pct"]["arr_equivalent"] == 12000


def test_ab_sample_size_matches_textbook() -> None:
    """@spec:AC-016 — 0,10 → 0,05, α 5%, poder 80% dá 435 por braço."""
    assert ab_sample_size(0.10, 0.05) == 435
    with pytest.raises(ValueError, match="diferentes"):
        ab_sample_size(0.1, 0.1)
