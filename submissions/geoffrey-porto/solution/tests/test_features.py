from __future__ import annotations

from datetime import date

from fixtures import make_tables, sub

from churn_diag.features import (
    QUARANTINED_UNDATED,
    RATE_FEATURES,
    rate_features,
)

T0 = date(2024, 10, 1)


def _tables():
    return make_tables(
        accounts=[
            {"account_id": "A-1"},  # uso e tickets
            {"account_id": "A-2"},  # sem uso, sem ticket
            {"account_id": "A-3"},  # uso antigo (fora da janela de 90 dias)
        ],
        subscriptions=[
            sub("S-1", date(2024, 1, 1), None, account_id="A-1"),
            sub("S-3", date(2024, 1, 1), None, account_id="A-3"),
        ],
        feature_usage=[
            {
                "usage_id": "U-1",
                "subscription_id": "S-1",
                "usage_date": date(2024, 9, 1),
                "usage_count": 100,
                "error_count": 2,
            },
            {
                "usage_id": "U-2",
                "subscription_id": "S-1",
                "usage_date": date(2024, 9, 20),
                "usage_count": 50,
                "error_count": 1,
            },
            {
                "usage_id": "U-3",
                "subscription_id": "S-3",
                "usage_date": date(2024, 1, 5),
                "usage_count": 10,
                "error_count": 0,
            },
        ],
        support_tickets=[
            {
                "ticket_id": "T-1",
                "account_id": "A-1",
                "submitted_at": date(2024, 9, 2),
                "escalation_flag": True,
                "satisfaction_score": None,
            },
            {
                "ticket_id": "T-2",
                "account_id": "A-1",
                "submitted_at": date(2024, 9, 3),
                "escalation_flag": False,
                "satisfaction_score": 4.0,
            },
            {
                "ticket_id": "T-3",
                "account_id": "A-1",
                "submitted_at": date(2024, 9, 4),
                "escalation_flag": False,
                "satisfaction_score": None,
            },
            {
                "ticket_id": "T-4",
                "account_id": "A-1",
                "submitted_at": date(2024, 9, 5),
                "escalation_flag": False,
                "satisfaction_score": 5.0,
            },
        ],
    )


def test_rates_match_hand_calculation() -> None:
    """@spec:AC-019 — 3 erros em 150 usos = 2,0; 1 escalada em 4 tickets = 0,25."""
    r = rate_features(_tables(), T0, window_days=90)
    a1 = r.filter(r["account_id"] == "A-1").row(0, named=True)
    assert a1["errors_per_100_uses"] == 2.0
    assert a1["escalation_rate"] == 0.25
    assert a1["satisfaction_missing_share"] == 0.5


def test_no_denominator_means_empty_not_zero() -> None:
    """@spec:AC-019 — sem uso ou sem ticket, a taxa fica vazia (nunca zero)."""
    r = rate_features(_tables(), T0, window_days=90)
    a2 = r.filter(r["account_id"] == "A-2").row(0, named=True)
    a3 = r.filter(r["account_id"] == "A-3").row(0, named=True)
    for col in RATE_FEATURES:
        assert a2[col] is None, col
    assert a3["errors_per_100_uses"] is None  # uso existe, mas fora da janela
    assert r.height == 3


def test_window_changes_the_denominator() -> None:
    """@spec:AC-019 — sem janela, o histórico inteiro entra no denominador."""
    full = rate_features(_tables(), T0, window_days=None)
    a3 = full.filter(full["account_id"] == "A-3").row(0, named=True)
    assert a3["uses"] == 10
    assert a3["errors_per_100_uses"] == 0.0  # 0 erros em 10 usos: taxa real, não vazio


def test_quarantine_list_is_declared_in_one_place() -> None:
    """@spec:AC-024 @principle:P-009 — as flags sem data ficam listadas num só lugar."""
    assert QUARANTINED_UNDATED == ("upgrade_flag", "downgrade_flag", "auto_renew_flag")
