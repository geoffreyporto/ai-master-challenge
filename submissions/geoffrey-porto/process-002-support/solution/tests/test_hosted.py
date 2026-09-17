"""Classificação hospedada: modelos definidos pelo dono, fallback e medição honesta."""

from __future__ import annotations

import json

from fakes import FakeClient

from support_redesign import config, hosted
from support_redesign.config import TOPICS
from support_redesign.pipeline import HOSTED_DIR


def test_primary_model_serves_and_fallback_takes_over():
    """@spec:AC-030 @principle:P-012"""
    ok = hosted.classify(FakeClient(), "laptop broken")
    assert ok["model_used"] == "fastino/gliner2-multi-large-v1"
    assert ok["fallback"] is False
    assert ok["label"] == "Hardware"
    fake = FakeClient(down={config.PIONEER_CLASSIFIER})
    fb = hosted.classify(fake, "laptop broken")
    assert fb["model_used"] == "fastino/gliner2-large-v1"
    assert fb["fallback"] is True
    assert [m for m, _ in fake.calls] == [
        config.PIONEER_CLASSIFIER,
        config.PIONEER_CLASSIFIER_FALLBACK,
    ]
    none = hosted.classify(
        FakeClient(
            down={config.PIONEER_CLASSIFIER, config.PIONEER_CLASSIFIER_FALLBACK}
        ),
        "x",
    )
    assert none["label"] is None


def test_hosted_classifier_measured_on_full_holdout(metrics):
    """@spec:AC-030"""
    b2 = metrics["hosted"]["b2_test"]
    assert b2["n"] == metrics["split"]["test"]
    assert set(b2["f1_per_class"]) == set(TOPICS)
    assert sum(b2["served_by"].values()) == b2["n"]
    assert set(b2["served_by"]) <= {
        config.PIONEER_CLASSIFIER,
        config.PIONEER_CLASSIFIER_FALLBACK,
    }
    cache = json.loads((HOSTED_DIR / "b2_test.json").read_text())
    unanswered = [v for v in cache.values() if v["label"] is None]
    assert b2["unparsed"] == len(unanswered)
    assert all(v["fallback"] for v in unanswered)
    assert b2 == metrics["classifier"]["test"][b2["model"]]


def test_llm_measured_on_seeded_stratified_sample(metrics, split):
    """@spec:AC-031 @principle:P-006"""
    ls = metrics["hosted"]["llm_sample"]
    sample = hosted.stratified_sample(split.test)
    assert ls["n"] == sample.height == 8 * config.LLM_SAMPLE_PER_CLASS
    assert (
        sample["Topic_group"].value_counts()["count"].to_list()
        == [config.LLM_SAMPLE_PER_CLASS] * 8
    )
    assert (
        hosted.stratified_sample(split.test)["row_id"].to_list()
        == sample["row_id"].to_list()
    )
    for key in ("llm", "b0", "b2"):
        assert ls[key]["n"] == ls["n"]
        assert 0 <= ls[key]["macro_f1"] <= 1
    assert ls["llm"]["served_by"] == {config.PIONEER_LLM: ls["n"]}
    assert ls["llm"]["median_client_ms"] > 0
    assert ls["llm"]["tokens_total"] > 0


def test_llm_answer_parsing():
    """@spec:AC-031"""
    assert hosted.parse_llm_label("Administrative rights") == "Administrative rights"
    assert hosted.parse_llm_label("queue: hr support.") == "HR Support"
    assert hosted.parse_llm_label("no idea") is None


def test_abstention_falls_back_to_the_large_model():
    """@spec:AC-030"""

    class Abstains(FakeClient):
        def infer(self, model_id, text, schema):
            self.calls.append((model_id, text))
            if model_id == config.PIONEER_CLASSIFIER:
                return {"result": {"topic_group": None}, "model_used": model_id}
            return super().infer(model_id, text, schema)

    fake = Abstains()
    out = hosted.classify(fake, "x")
    assert out["model_used"] == config.PIONEER_CLASSIFIER_FALLBACK
    assert out["fallback"] is True
    assert out["label"] == "Hardware"
