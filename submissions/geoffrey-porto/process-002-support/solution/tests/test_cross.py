"""Cruzamento: o roteador precisa saber quando não sabe."""

from __future__ import annotations

import polars as pl

from support_redesign.config import OUTPUTS_DIR, TOPICS


def test_every_dataset1_ticket_is_scored(metrics, d1):
    """@spec:AC-021"""
    scored = pl.read_parquet(OUTPUTS_DIR / "d1_scored.parquet")
    assert scored.height == d1.height == 8469
    assert scored["Ticket ID"].n_unique() == d1.height
    assert set(scored["predicted_topic"].unique()) <= set(TOPICS)
    assert scored["action"].null_count() == 0
    assert (
        sum(metrics["cross"]["topic_share_d1"].values()) == 1.0
        or abs(sum(metrics["cross"]["topic_share_d1"].values()) - 1.0) < 1e-9
    )


def test_domain_shift_is_tested_and_changes_the_action(metrics):
    """@spec:AC-022"""
    c = metrics["cross"]
    assert c["ks_p"] < 0.001
    assert c["median_known_d1"] < c["median_known_d2_test"]
    assert c["human_share_d1"] > c["human_share_d2_test"]
    assert c["human_share_d1"] > 0.9
