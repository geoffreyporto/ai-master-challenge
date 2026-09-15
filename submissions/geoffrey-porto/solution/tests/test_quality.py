from __future__ import annotations

from datetime import date

from fixtures import frame, make_tables, sub

from churn_diag.loader import Tables
from churn_diag.quality import (
    churn_definition_agreement,
    dedupe_exact,
    id_collisions,
    quality_report,
    timeline_violations,
)


def test_timeline_violations_are_counted_exactly() -> None:
    """@spec:AC-002 — uso antes da assinatura, ticket antes do cadastro, churn precoce."""
    t = make_tables(
        accounts=[{"account_id": "A-1", "signup_date": date(2024, 3, 1)}],
        subscriptions=[sub("S-1", date(2024, 3, 1), date(2024, 5, 1))],
        feature_usage=[
            {"usage_id": "U-1", "usage_date": date(2024, 2, 1)},  # antes do início
            {"usage_id": "U-2", "usage_date": date(2024, 4, 1)},  # ok
            {"usage_id": "U-3", "usage_date": date(2024, 6, 1)},  # depois do fim
        ],
        support_tickets=[
            {
                "ticket_id": "T-1",
                "submitted_at": date(2024, 1, 15),
            },  # antes do cadastro
            {"ticket_id": "T-2", "submitted_at": date(2024, 3, 15)},
        ],
        churn_events=[{"churn_event_id": "C-1", "churn_date": date(2024, 2, 1)}],
    )
    v = timeline_violations(t)
    assert v["usage_before_sub_start"] == 1
    assert v["usage_before_sub_start_pct"] == 33.3
    assert v["usage_after_sub_end"] == 1
    assert v["tickets_before_signup"] == 1
    assert v["tickets_before_signup_pct"] == 50.0
    assert v["churn_events_before_first_sub"] == 1


def test_real_data_timeline_problems_are_reported(real_tables: Tables) -> None:
    """@spec:AC-002 — no dado real, a auditoria expõe a quebra de linha do tempo."""
    v = quality_report(real_tables)["timeline"]
    assert v["usage_before_sub_start_pct"] > 50  # uso antes da assinatura existir
    assert v["tickets_before_signup_pct"] > 25
    assert v["subs_end_before_start"] == 0  # a única linha do tempo consistente


def test_same_id_different_content_is_kept() -> None:
    """@spec:AC-003 — IDs colididos permanecem; só linha idêntica é removida."""
    usage = frame(
        "feature_usage",
        [
            {"usage_id": "U-9", "usage_count": 3},
            {"usage_id": "U-9", "usage_count": 7},  # mesmo ID, conteúdo diferente
            {"usage_id": "U-5", "usage_count": 1},
            {"usage_id": "U-5", "usage_count": 1},  # duplicata exata
        ],
    )
    out, removed = dedupe_exact(usage)
    assert removed == 1
    assert out.height == 3
    assert sorted(out.filter(out["usage_id"] == "U-9")["usage_count"].to_list()) == [
        3,
        7,
    ]
    assert id_collisions(usage, "usage_id") == 1


def test_churn_definitions_disagreement_is_visible() -> None:
    """@spec:AC-004 — contas por definição e divergências entre as três."""
    t = make_tables(
        accounts=[
            {"account_id": "A-1", "churn_flag": True},
            {"account_id": "A-2", "churn_flag": False},
            {"account_id": "A-3", "churn_flag": False},
        ],
        subscriptions=[
            sub("S-1", date(2024, 1, 1), date(2024, 2, 1), account_id="A-1"),
            sub("S-2", date(2024, 1, 1), None, account_id="A-2"),
            sub("S-3", date(2024, 1, 1), None, account_id="A-3"),
        ],
        churn_events=[
            {"churn_event_id": "C-1", "account_id": "A-1"},
            {"churn_event_id": "C-2", "account_id": "A-2"},
        ],
    )
    a = churn_definition_agreement(t)
    assert (a["flag_account"], a["has_churn_event"], a["has_ended_subscription"]) == (
        1,
        2,
        1,
    )
    assert a["all_three_agree_churn"] == 1
    assert a["all_three_agree_active"] == 1
    assert a["disagree"] == 1
    assert a["event_but_flag_false"] == 1
