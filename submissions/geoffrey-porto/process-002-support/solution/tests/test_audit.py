"""Auditoria: o veredito precisa vir com a evidência, não com a opinião."""

from __future__ import annotations

from support_redesign.audit import (
    UNIFORM_COLUMNS,
    audit_d1,
    audit_d2,
    readme_divergences,
)


def test_dataset1_is_declared_synthetic_with_evidence(d1):
    """@spec:AC-001"""
    out = audit_d1(d1)
    ev = out["evidence"]
    assert out["verdict"] == "sintetico"
    assert ev["product_placeholder_share"] == 1.0
    assert set(ev["uniform_chi2_p"]) == set(UNIFORM_COLUMNS)
    assert min(ev["uniform_chi2_p"].values()) > 0.05
    assert 0.49 < ev["negative_interval_share"] < 0.50
    assert ev["email_domains"] == ["example.com", "example.net", "example.org"]
    assert ev["resolution_unique_share"] == 1.0


def test_dataset2_is_declared_real_preprocessed_with_evidence(d2):
    """@spec:AC-002"""
    out = audit_d2(d2)
    ev = out["evidence"]
    assert out["verdict"] == "real_preprocessado"
    assert ev["placeholders"] == 0
    assert ev["duplicates"] == 0
    assert ev["conflicting_labels"] == 0
    assert ev["classes"] == 8
    assert ev["imbalance_ratio"] > 7
    assert ev["docs_with_uppercase"] == 0
    assert ev["docs_with_digits"] == 0


def test_readme_divergences_are_declared(d1):
    """@spec:AC-003"""
    div = {d["item"]: d for d in readme_divergences(d1)}
    assert div["Linhas do Dataset 1"]["medido"] == 8469
    assert div["Linhas do Dataset 1"]["readme"] == 30000
    assert div["Valores de Ticket Type"] == {
        "item": "Valores de Ticket Type",
        "readme": 3,
        "medido": 5,
    }
