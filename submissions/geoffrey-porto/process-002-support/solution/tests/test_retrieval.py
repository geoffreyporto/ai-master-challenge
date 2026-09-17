"""Índice de similares: sem vazamento do teste, medido no hold-out inteiro."""

from __future__ import annotations

import json

import numpy as np

from support_redesign.config import OUTPUTS_DIR, README_FILE
from support_redesign.retrieval import SimilarIndex, chance_recall_at_k, recall_at_k


def test_index_is_built_from_train_only(metrics, split):
    """@spec:AC-018 @principle:P-002"""
    ids = set(json.loads((OUTPUTS_DIR / "models" / "index_ids.json").read_text()))
    assert ids == set(split.train["row_id"].to_list())
    assert not ids & set(split.test["row_id"].to_list())
    assert metrics["retrieval"]["index_size"] == split.train.height


def test_recall_at_k_on_full_holdout_beats_chance(metrics):
    """@spec:AC-019"""
    r, c = metrics["retrieval"]["recall"], metrics["retrieval"]["chance"]
    assert set(r) == {"recall@1", "recall@5", "recall@10"}
    assert r["recall@1"] <= r["recall@5"] <= r["recall@10"]
    assert r["recall@5"] > c["recall@5"] + 0.2


def test_recall_and_chance_math():
    """@spec:AC-019"""
    emb = np.array([[1.0, 0.0], [0.0, 1.0], [0.9, 0.1]])
    index = SimilarIndex(emb, ["x", "y", "x"], ["a", "b", "c"], [0, 1, 2])
    queries = np.array([[1.0, 0.05], [0.05, 1.0]])
    assert recall_at_k(index, queries, ["x", "x"], [1, 2]) == {
        "recall@1": 0.5,
        "recall@2": 1.0,
    }
    chance = chance_recall_at_k(["x", "y"], ["x"], [1, 2])
    assert chance == {"recall@1": 0.5, "recall@2": 0.75}


def test_resolution_limitation_is_declared_in_report():
    """@spec:AC-020"""
    text = README_FILE.read_text()
    assert "Recall@" in text
    assert "resoluções do Dataset 1 são sintéticas" in text
    assert "mede a fila, não a qualidade da resposta" in text
