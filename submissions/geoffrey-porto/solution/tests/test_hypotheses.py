from __future__ import annotations

import pytest

from churn_diag.hypotheses import (
    CLAIM_TYPES,
    Context,
    Finding,
    holm,
    invariance_table,
    run_all,
)
from churn_diag.loader import Tables
from churn_diag.metrics import exposure_panel
from churn_diag.risk import oot_validation

ALL_TABLES = {
    "accounts",
    "subscriptions",
    "feature_usage",
    "support_tickets",
    "churn_events",
}


@pytest.fixture(scope="module")
def findings(real_tables: Tables) -> list[Finding]:
    panel = exposure_panel(real_tables.subscriptions)
    return run_all(Context(real_tables, panel, oot_validation(real_tables)))


def test_each_hypothesis_has_test_effect_and_tables(findings: list[Finding]) -> None:
    """@spec:AC-008 — estatística, p ajustado, efeito e tabelas; juntas cruzam as cinco."""
    assert len(findings) >= 8
    for f in findings:
        assert f.test
        assert f.effect_name
        assert f.p_holm is not None
        assert 0.0 <= f.p_value <= f.p_holm <= 1.0
        assert f.tables
    assert set().union(*(f.tables for f in findings)) == ALL_TABLES


def test_holm_matches_reference_values() -> None:
    """@spec:AC-009 — Holm confere com valores calculados à mão."""
    assert holm([0.01, 0.04, 0.03, 0.005]) == pytest.approx([0.03, 0.06, 0.06, 0.02])
    assert holm([0.5, 0.9]) == pytest.approx([1.0, 1.0])  # teto em 1


def test_every_finding_has_one_claim_label(findings: list[Finding]) -> None:
    """@spec:AC-010 @principle:P-004 — rótulo único; hipótese causal traz o experimento."""
    for f in findings:
        assert f.claim_type in CLAIM_TYPES
        if f.claim_type == "hipotese_causal":
            assert f.validation, f"{f.id} é causal e não diz como validar"


def test_age_effect_is_reported_per_environment(real_tables: Tables) -> None:
    """@spec:AC-011 — razão de risco jovem/madura por indústria, plano e canal."""
    inv = invariance_table(real_tables, exposure_panel(real_tables.subscriptions))
    assert set(inv["env_type"].unique()) == {"industry", "plan_tier", "referral_source"}
    assert {"hr", "ci_low", "ci_high", "direction", "stable_in_type"} <= set(
        inv.columns
    )
    assert (inv["ci_low"] <= inv["hr"]).all()
    assert (inv["hr"] <= inv["ci_high"]).all()
