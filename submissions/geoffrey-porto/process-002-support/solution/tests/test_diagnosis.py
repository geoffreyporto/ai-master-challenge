"""Diagnóstico: resultado nulo só vale com poder, e todo achado diz de onde vem."""

from __future__ import annotations

import pytest

from support_redesign.diagnosis import DIMENSIONS, diagnose


@pytest.fixture(scope="module")
def diag(d1):
    return diagnose(d1)


def test_segments_cover_channel_priority_type(diag):
    """@spec:AC-004"""
    seg = diag["segments"]
    assert seg.height == 80
    assert set(seg.columns) >= {*DIMENSIONS, "n", "median_hours", "csat_mean"}
    assert seg["n"].sum() == 2769
    worst = diag["findings"][0]
    assert worst["id"] == "F-01" and worst["base"] == "sintetico"
    top = seg.row(0, named=True)
    assert top["Ticket Channel"] in worst["texto"]


def test_each_dimension_has_test_effect_and_power(diag):
    """@spec:AC-005"""
    tests = diag["tests"]
    assert len(tests) == 6
    for t in tests.values():
        assert 0 <= t["p"] <= 1
        assert 0 <= t["epsilon2"] < 0.01
    mde = diag["mde"]
    assert mde["n_min_per_channel"] >= 600
    assert 0.15 < mde["mde_points"] < 0.30
    assert diag["no_detectable_driver"] == all(t["p"] >= 0.05 for t in tests.values())
    assert diag["no_detectable_driver"] is True


def test_ordinal_csat_model_is_reported(diag):
    """@spec:AC-006"""
    o = diag["ordinal"]
    assert o["n"] == 2769
    assert 0 <= o["pseudo_r2"] < 0.01
    assert o["lr_p"] > 0.05


def test_waste_is_not_computed_from_the_file(diag):
    """@spec:AC-007"""
    w = diag["waste"]
    assert w["hours"] is None and w["lacuna"] is True
    assert "cenário de ROI" in w["motivo"]
    assert sum(diag["status_mix"].values()) == pytest.approx(1.0)
    assert set(diag["status_mix"]) == {"Open", "Closed", "Pending Customer Response"}


def test_every_finding_declares_base_and_claim_type(diag):
    """@spec:AC-008 @principle:P-007"""
    assert diag["findings"]
    for f in diag["findings"]:
        assert f["base"] in {"sintetico", "real"}
        assert f["tipo"] in {"descricao", "predicao", "cenario"}
