from __future__ import annotations

from datetime import date

import polars as pl
import pytest
from fixtures import frame, sub

from churn_diag.metrics import (
    control_flags,
    exposure_panel,
    monthly_churn,
    standardized_ratio,
)


def test_monthly_rate_uses_active_base_on_first_day() -> None:
    """@spec:AC-005 — taxa = encerradas no mês ÷ ativas no 1º dia (contagem e MRR)."""
    subs = frame(
        "subscriptions",
        [
            sub("S-1", date(2024, 1, 1), None, mrr_amount=100),
            sub("S-2", date(2024, 1, 1), date(2024, 2, 10), mrr_amount=300),
            sub("S-3", date(2024, 1, 15), None, mrr_amount=50),
            sub(
                "S-4", date(2024, 2, 5), date(2024, 2, 20), mrr_amount=999
            ),  # nasceu no mês
            sub("S-5", date(2024, 1, 1), None, mrr_amount=0, is_trial=True),
        ],
    )
    m = monthly_churn(exposure_panel(subs, date(2024, 1, 1), date(2024, 2, 1)))
    feb = m.filter(pl.col("month") == date(2024, 2, 1)).row(0, named=True)
    assert feb["active_subs"] == 4  # S-1, S-2, S-3, S-5 no 1º dia
    assert feb["churned_subs"] == 1  # S-2 (S-4 não estava no 1º dia)
    assert feb["sub_churn_rate"] == pytest.approx(0.25)
    assert feb["active_mrr"] == 450  # trial não entra no MRR
    assert feb["mrr_churn_rate"] == pytest.approx(300 / 450, abs=1e-5)
    assert feb["ended_all"] == 2  # a contagem bruta inclui S-4


def _panel(rows: list[tuple[str, str, int, int]]) -> pl.DataFrame:
    """Painel sintético: (período, faixa, exposições, eventos), MRR 100 cada."""
    records = []
    for period, bucket, n, events in rows:
        records += [
            {
                "period": period,
                "age_bucket": bucket,
                "ended": i < events,
                "paid_mrr": 100,
            }
            for i in range(n)
        ]
    return pl.DataFrame(records)


def test_mix_change_alone_gives_ratio_one() -> None:
    """@spec:AC-006 — só o mix de idades mudou → observado/esperado ≈ 1."""
    p = _panel(
        [
            ("reference", "novo", 1000, 10),
            ("reference", "maduro", 1000, 50),
            ("target", "novo", 1800, 18),
            ("target", "maduro", 200, 10),
        ]
    )
    assert standardized_ratio(p)["ratio"] == pytest.approx(1.0)


def test_doubled_hazard_gives_ratio_two() -> None:
    """@spec:AC-006 — risco por faixa dobrou → observado/esperado ≈ 2."""
    p = _panel(
        [
            ("reference", "novo", 1000, 10),
            ("reference", "maduro", 1000, 50),
            ("target", "novo", 1000, 20),
            ("target", "maduro", 1000, 100),
        ]
    )
    s = standardized_ratio(p)
    assert s["ratio"] == pytest.approx(2.0)
    assert s["p_value"] < 0.001


def test_months_above_control_limit_are_flagged() -> None:
    """@spec:AC-007 — mês acima de média + 3σ da referência vira quebra."""
    series = pl.DataFrame(
        {
            "month": pl.date_range(
                date(2024, 1, 1), date(2024, 12, 1), "1mo", eager=True
            ),
            "rate": [
                0.010,
                0.011,
                0.009,
                0.010,
                0.012,
                0.008,
                0.010,
                0.011,
                0.009,
                0.011,
                0.020,
                0.035,
            ],
            "period": ["reference"] * 9 + ["target"] * 3,
        }
    )
    out = control_flags(series, "rate", pl.col("period") == "reference", k=3)
    assert out["is_break"].to_list() == [False] * 10 + [True, True]
