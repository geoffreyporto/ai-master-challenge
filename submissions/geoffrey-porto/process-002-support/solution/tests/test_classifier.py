"""Classificador: número só vale no hold-out, e o vencedor sai da validação."""

from __future__ import annotations

import numpy as np

from support_redesign.classifier import expected_calibration_error, pick_production
from support_redesign.config import TOPICS
from support_redesign.io import split_d2


def test_split_is_deterministic_stratified_and_disjoint(d2, split):
    """@spec:AC-009 @principle:P-002 @principle:P-006"""
    n = d2.height
    sizes = [split.train.height, split.val.height, split.test.height]
    assert sum(sizes) == n
    assert [round(s / n, 2) for s in sizes] == [0.70, 0.10, 0.20]
    ids = [set(p["row_id"].to_list()) for p in (split.train, split.val, split.test)]
    assert not (ids[0] & ids[1]) and not (ids[0] & ids[2]) and not (ids[1] & ids[2])
    docs = [set(p["Document"].to_list()) for p in (split.train, split.test)]
    assert not (docs[0] & docs[1])
    full = (
        d2["Topic_group"].value_counts(normalize=True).sort("Topic_group")["proportion"]
    )
    for part in (split.train, split.val, split.test):
        shares = part["Topic_group"].value_counts(normalize=True).sort("Topic_group")
        assert np.allclose(shares["proportion"], full, atol=0.005)
    again = split_d2(d2)
    assert again.test["row_id"].to_list() == split.test["row_id"].to_list()


def test_baseline_macro_f1_on_holdout(metrics):
    """@spec:AC-010 @principle:P-002"""
    b0 = metrics["classifier"]["test"]["B0 TF-IDF + LR"]
    assert b0["n"] == metrics["split"]["test"]
    assert b0["macro_f1"] >= 0.85
    assert set(b0["f1_per_class"]) == set(TOPICS)


def test_static_embeddings_compared_and_winner_picked_on_validation(metrics):
    """@spec:AC-011 @principle:P-002"""
    clf = metrics["classifier"]
    val = {k: v["macro_f1"] for k, v in clf["val"].items()}
    assert {"B0 TF-IDF + LR", "B1 Model2Vec + LR"} <= set(val)
    assert clf["production"] == pick_production(val)
    for name in val:
        assert clf["test"][name]["ms_per_ticket"] > 0
    assert pick_production({"a": 0.9, "b": 0.8}) == "a"


def test_calibration_error_is_reported(metrics):
    """@spec:AC-012"""
    ece = metrics["classifier"]["test"]["B0 TF-IDF + LR"]["ece"]
    assert 0 <= ece < 0.15
    perfect = np.array([[1.0, 0.0], [0.0, 1.0]])
    assert expected_calibration_error(perfect, np.array([0, 1])) == 0.0
    wrong = np.array([[1.0, 0.0]])
    assert expected_calibration_error(wrong, np.array([1])) == 1.0


def test_same_input_same_probabilities(production, split):
    """@principle:P-006"""
    clf = production["clf"]
    texts = split.test["Document"].head(50).to_list()
    assert np.array_equal(clf.predict_proba(texts), clf.predict_proba(texts))
