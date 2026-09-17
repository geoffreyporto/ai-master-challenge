"""Segunda opinião: só entra se a validação provar a precisão."""

from __future__ import annotations

import numpy as np

from support_redesign.boundary import Decision, second_opinion, second_opinion_eligible
from support_redesign.config import TARGET_PRECISION


def _d(rule: str, topic: str = "A") -> Decision:
    action = "auto" if rule == "auto" else "humano"
    return Decision(topic, 0.5, 0.1, (topic,), action, rule, rule)


def test_only_uncertainty_cases_are_eligible():
    """@spec:AC-032 @principle:P-004"""
    ds = [
        _d("low_confidence"),
        _d("conformal"),
        _d("human_only"),
        _d("ood"),
        _d("auto"),
    ]
    assert second_opinion_eligible(ds) == [0, 1]


def test_rule_is_enabled_only_with_validated_precision():
    """@spec:AC-032"""
    ds = [_d("low_confidence")] * 30
    y_good = np.zeros(30, dtype=int)
    labels = dict.fromkeys(range(30), "A")
    good = second_opinion(ds, y_good, ("A", "B"), labels, 0.95)
    assert good["enabled"] is True
    assert good["precision"] == 1.0
    y_bad = np.array([0] * 20 + [1] * 10)
    assert second_opinion(ds, y_bad, ("A", "B"), labels, 0.95)["enabled"] is False
    few = second_opinion(
        ds[:5], y_good[:5], ("A", "B"), dict.fromkeys(range(5), "A"), 0.95
    )
    assert few["enabled"] is False


def test_second_opinion_reported_on_validation_and_test(metrics):
    """@spec:AC-032 @principle:P-002"""
    so = metrics["hosted"]["second_opinion"]
    val, test = so["val"], so["test"]
    assert val["eligible"] > 0
    assert test["eligible"] > 0
    assert test["enabled"] == val["enabled"]
    assert val["enabled"] == (
        val["precision"] is not None
        and val["agree"] >= 20
        and val["precision"] >= TARGET_PRECISION
    )
    assert (
        0 <= test["extra_coverage"] < 1 - metrics["boundary"]["test"]["coverage_auto"]
    )
