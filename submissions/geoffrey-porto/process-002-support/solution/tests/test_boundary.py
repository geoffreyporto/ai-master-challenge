"""Fronteira: automatizar só onde o erro é raro, e nunca tudo."""

from __future__ import annotations

import numpy as np
import pytest

from support_redesign.boundary import (
    Policy,
    class_thresholds,
    conformal_qhat,
    decide,
    decide_all,
    fit_policy,
    human_examples,
)
from support_redesign.classifier import label_index
from support_redesign.config import TARGET_PRECISION

CLASSES = ("A", "B", "Miscellaneous")


def _policy(**kw) -> Policy:
    base = dict(
        classes=CLASSES,
        thresholds={"A": 0.6, "B": None, "Miscellaneous": 0.5},
        qhat=0.5,
        min_known_share=0.3,
    )
    return Policy(**{**base, **kw})


def test_thresholds_come_from_validation_only(production, split, metrics):
    """@spec:AC-013 @principle:P-002"""
    clf, policy = production["clf"], production["policy"]
    va = split.val
    p_val = clf.predict_proba(va["Document"].to_list())
    y_val = label_index(clf.classes_, va["Topic_group"].to_list())
    refit = fit_policy(
        p_val, y_val, clf.classes_, clf.known_share(va["Document"].to_list())
    )
    assert refit == policy
    pred = p_val.argmax(axis=1)
    for c, name in enumerate(clf.classes_):
        thr = policy.thresholds[name]
        if thr is None:
            continue
        m = (pred == c) & (p_val.max(axis=1) >= thr)
        assert (y_val[m] == c).mean() >= TARGET_PRECISION


def test_class_without_viable_threshold_is_human_only():
    """@spec:AC-013"""
    proba = np.array([[0.9, 0.1]] * 30)
    y = np.array([1] * 30)
    assert class_thresholds(proba, y, ("A", "B"), 0.95)["A"] is None


def test_policy_meets_precision_without_automating_everything(metrics):
    """@spec:AC-014 @principle:P-004"""
    t = metrics["boundary"]["test"]
    assert t["precision_auto"] >= TARGET_PRECISION - 0.02
    assert 0 < t["coverage_auto"] < 1
    assert t["human_share"] > 0
    assert t["coverage_auto"] + t["human_share"] + t["confirm_share"] == pytest.approx(
        1
    )


def test_risky_cases_never_leave_without_a_human():
    """@spec:AC-015 @principle:P-004"""
    p = _policy()
    assert decide(p, np.array([0.1, 0.1, 0.8])).action == "humano"  # Miscellaneous
    assert decide(p, np.array([0.1, 0.8, 0.1])).action == "humano"  # fila sem limiar
    two = decide(p, np.array([0.5, 0.5, 0.0]))
    assert two.action == "humano" and "conformal" in two.reason
    assert decide(p, np.array([0.9, 0.05, 0.05]), "Critical").action == "confirmar"
    assert decide(p, np.array([0.9, 0.05, 0.05])).action == "auto"
    ood = decide(p, np.array([0.9, 0.05, 0.05]), known_share=0.1)
    assert ood.action == "humano" and "domínio" in ood.reason


def test_production_policy_keeps_misc_and_critical_human(production, split):
    """@spec:AC-015 @principle:P-004"""
    clf, policy = production["clf"], production["policy"]
    texts = split.test["Document"].to_list()
    proba = clf.predict_proba(texts)
    crit = decide_all(policy, proba, ["Critical"] * len(texts), clf.known_share(texts))
    assert all(d.action != "auto" for d in crit)
    assert all(d.action == "humano" for d in crit if d.topic == "Miscellaneous")


def test_conformal_sets_keep_their_promise(metrics):
    """@spec:AC-016"""
    t = metrics["boundary"]["test"]
    alpha = metrics["boundary"]["policy"]["alpha"]
    assert t["conformal_coverage"] >= 1 - alpha - 0.02
    scores = np.array([[0.9, 0.1], [0.2, 0.8], [0.6, 0.4]])
    assert conformal_qhat(scores, np.array([0, 1, 1]), 0.1) == pytest.approx(0.6)


def test_human_examples_are_seeded_samples_not_picks(metrics, production, split):
    """@spec:AC-017"""
    ex = metrics["boundary"]["human_examples"]
    assert len(ex) == 8
    for e in ex:
        assert set(e) == {
            "texto",
            "fila_verdadeira",
            "fila_prevista",
            "confianca",
            "motivo",
        }
    clf, policy = production["clf"], production["policy"]
    texts = split.test["Document"].to_list()
    labels = split.test["Topic_group"].to_list()
    dec = decide_all(policy, clf.predict_proba(texts), known=clf.known_share(texts))
    assert human_examples(texts, labels, dec) == ex
    assert human_examples(texts, labels, dec, seed=7) != ex
