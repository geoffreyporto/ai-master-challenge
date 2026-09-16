from __future__ import annotations

import polars as pl
import pytest

from churn_diag.features import (
    FRICTION_COMPONENTS,
    attach_derived_features,
    zscore_stats,
)


def _panel(rows: list[dict]) -> pl.DataFrame:
    base = {
        "active_seats": 10,
        "usage_total_90d": 100,
        "tickets_90d": 2.0,
        "escalation_rate_90d": 0.0,
        "response_time_p90_90d": 100.0,
        "high_priority_ticket_share_90d": 0.0,
        "split": "treino",
    }
    return pl.DataFrame([{**base, **r} for r in rows])


def test_usage_per_seat_divides_by_active_seats() -> None:
    """@spec:AC-027 — uso da janela ÷ assentos ativos (mínimo 1)."""
    panel = _panel(
        [
            {"usage_total_90d": 300, "active_seats": 10},
            {"usage_total_90d": None, "active_seats": 4},  # sem uso na janela
            {"usage_total_90d": 50, "active_seats": 0},  # guarda do mínimo 1
        ]
    )
    out = attach_derived_features(panel, zscore_stats(panel))
    assert out["usage_per_active_seat_90d"].to_list() == [30.0, 0.0, 50.0]


def test_friction_index_is_empty_without_tickets() -> None:
    """@spec:AC-028 — sem ticket na janela, o índice é vazio (não zero)."""
    panel = _panel(
        [
            {"tickets_90d": 2.0},
            dict.fromkeys(FRICTION_COMPONENTS),
        ]
    )
    out = attach_derived_features(panel, zscore_stats(panel))
    values = out["support_friction_index"].to_list()
    assert values[0] is not None
    assert values[1] is None


def test_zscore_parameters_come_from_training_only() -> None:
    """@spec:AC-028 — média e desvio do treino; o teste não entra na conta."""
    train = _panel(
        [
            {"tickets_90d": 1.0},
            {"tickets_90d": 3.0},
            {"tickets_90d": 5.0},
        ]
    )
    stats = zscore_stats(train)
    mean, std = stats["tickets_90d"]
    assert mean == pytest.approx(3.0)
    assert std == pytest.approx(2.0)

    # As outras três componentes são constantes no treino, então o z delas é 0:
    # o índice da linha de teste é exatamente o z de tickets com stats do treino.
    test = _panel([{"tickets_90d": 1000.0}])
    out = attach_derived_features(test, stats)
    assert out["support_friction_index"][0] == pytest.approx((1000.0 - mean) / std)

    # ...e ajustar no painel inteiro daria outro número (é o vazamento evitado).
    leaky = zscore_stats(pl.concat([train, test], how="vertical_relaxed"))
    assert leaky["tickets_90d"] != stats["tickets_90d"]
