"""ROI: cada número diz de onde vem, e o erro da IA é descontado."""

from __future__ import annotations

import re

import pytest

from support_redesign.config import ASSUMPTIONS_FILE
from support_redesign.roi import BANDS, ORIGINS, load_assumptions, scenario


def test_every_parameter_declares_its_origin():
    """@spec:AC-023 @principle:P-007"""
    a = load_assumptions(ASSUMPTIONS_FILE)
    assert a
    for name, param in a.items():
        assert param["origem"] in ORIGINS, name
        assert param.get("fonte"), name
        if param["origem"] == "premissa":
            assert re.fullmatch(r"Q-\d{3}", param["pergunta"]), name
        if param["origem"] != "medido":
            assert "valor" in param, name


def test_net_hours_discount_ai_errors(metrics):
    """@spec:AC-024"""
    a = load_assumptions(ASSUMPTIONS_FILE)
    t = metrics["boundary"]["test"]
    roi = metrics["roi"]
    assert set(roi) == set(BANDS)
    for band in BANDS:
        assert roi[band] == scenario(a, t["coverage_auto"], t["precision_auto"], band)
    base = roi["base"]
    assert base["tickets_month"] == 2500
    expected_saved = 2500 * t["coverage_auto"] * 3 / 60
    expected_rework = 2500 * t["coverage_auto"] * (1 - t["precision_auto"]) * 15 / 60
    assert base["triage_hours_saved_month"] == pytest.approx(expected_saved)
    assert base["rework_hours_month"] == pytest.approx(expected_rework)
    assert base["net_hours_month"] == pytest.approx(expected_saved - expected_rework)
    assert base["net_brl_year"] == pytest.approx(base["net_hours_month"] * 60 * 12)
    assert (
        roi["baixa"]["net_hours_month"]
        < base["net_hours_month"]
        < roi["alta"]["net_hours_month"]
    )


def test_perfect_router_has_no_rework():
    """@spec:AC-024"""
    a = load_assumptions(ASSUMPTIONS_FILE)
    out = scenario(a, coverage=0.5, precision=1.0, band="base")
    assert out["rework_hours_month"] == 0
    assert out["net_hours_month"] == pytest.approx(2500 * 0.5 * 3 / 60)
