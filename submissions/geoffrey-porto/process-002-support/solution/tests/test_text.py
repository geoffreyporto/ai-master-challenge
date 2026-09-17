"""Normalização: a mesma regra no treino, no app e no roteador."""

from __future__ import annotations

from support_redesign.text import analyzer, normalize


def test_normalize_rules_match_router_unit_tests():
    """@principle:P-005"""
    assert (
        normalize("I'm having an issue with the {product_purchased}. Error 404!")
        == "i m having an issue with the error"
    )
    assert normalize("{a{b}c}") == "a c"
    assert normalize("   ") == ""
    assert analyzer("VPN a down now") == ["vpn", "down", "now", "vpn down", "down now"]


def test_dataset2_text_is_already_normalized(split):
    """@principle:P-005"""
    docs = split.test["Document"].head(500).to_list()
    assert sum(normalize(d) == " ".join(d.split()) for d in docs) >= 495
