"""Cruzamento: o classificador do Dataset 2 aplicado ao Dataset 1 (cruzamento-datasets)."""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from typing import Any

import numpy as np
import polars as pl
from scipy import stats

from support_redesign.boundary import Decision, Policy, decide_all
from support_redesign.classifier import TfidfLR


def score_d1(
    clf: TfidfLR, policy: Policy, d1: pl.DataFrame
) -> tuple[pl.DataFrame, np.ndarray]:
    texts = (d1["Ticket Subject"] + " " + d1["Ticket Description"]).to_list()
    proba = clf.predict_proba(texts)
    known = clf.known_share(texts)
    decisions = decide_all(policy, proba, d1["Ticket Priority"].to_list(), known)
    scored = d1.select("Ticket ID", "Ticket Type", "Ticket Priority").with_columns(
        pl.Series("predicted_topic", [d.topic for d in decisions]),
        pl.Series("confidence", [d.confidence for d in decisions]),
        pl.Series("known_share", known),
        pl.Series("action", [d.action for d in decisions]),
        pl.Series("reason", [d.reason for d in decisions]),
    )
    return scored, proba


def _share(decisions: Sequence[Decision] | pl.Series, action: str) -> float:
    actions = (
        [d.action for d in decisions]
        if not isinstance(decisions, pl.Series)
        else decisions.to_list()
    )
    return float(np.mean([a == action for a in actions]))


def domain_shift(
    scored_d1: pl.DataFrame, test_conf: np.ndarray, test_decisions: Sequence[Decision]
) -> dict[str, Any]:
    d1_conf = scored_d1["confidence"].to_numpy()
    ks = stats.ks_2samp(d1_conf, test_conf)
    topics = Counter(scored_d1["predicted_topic"].to_list())
    return {
        "n_d1": scored_d1.height,
        "ks_stat": float(ks.statistic),
        "ks_p": float(ks.pvalue),
        "median_conf_d1": float(np.median(d1_conf)),
        "median_conf_d2_test": float(np.median(test_conf)),
        "human_share_d1": _share(scored_d1["action"], "humano"),
        "human_share_d2_test": _share(test_decisions, "humano"),
        "auto_share_d1": _share(scored_d1["action"], "auto"),
        "topic_share_d1": {k: v / scored_d1.height for k, v in topics.most_common()},
    }
