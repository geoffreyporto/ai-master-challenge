"""Privacidade: máscara antes do LLM, guardrail depois."""

from __future__ import annotations

import pytest
from fakes import FakeClient

from support_redesign import config, privacy
from support_redesign.drafting import draft_reply
from support_redesign.pioneer import PioneerUnavailableError

TEXT = privacy.with_customer_pii(
    "My tv is broken.", "Marisa Obrien", "carroll@example.com"
)


def test_mask_replaces_pii_with_typed_placeholders():
    """@spec:AC-033 @principle:P-012"""
    fake = FakeClient()
    out = privacy.mask(fake, TEXT)
    assert "Marisa Obrien" not in out.text
    assert "carroll@example.com" not in out.text
    assert "[PERSON]" in out.text
    assert "[EMAIL]" in out.text
    assert fake.calls[0][0] == "fastino/gliner2-privacy-filter-PII-multi"


def test_masking_recall_on_seeded_sample(metrics, d1):
    """@spec:AC-033 @principle:P-006"""
    p = metrics["hosted"]["privacy"]
    assert p["n"] == config.PII_SAMPLE_SIZE
    assert p["name_recall"] >= 0.90
    assert p["email_recall"] >= 0.95
    assert privacy.pii_sample(d1).equals(privacy.pii_sample(d1))


def test_nothing_reaches_the_llm_unmasked():
    """@spec:AC-034 @principle:P-013"""
    fake = FakeClient()
    draft_reply(fake, TEXT, "Hardware", ["similar ticket"])
    llm_calls = [text for model, text in fake.calls if model == config.PIONEER_LLM]
    assert len(llm_calls) == 1
    assert "Marisa Obrien" not in llm_calls[0]
    assert "carroll@example.com" not in llm_calls[0]


def test_privacy_failure_blocks_the_llm_call():
    """@spec:AC-034 @principle:P-013"""
    fake = FakeClient(fail_privacy=True)
    with pytest.raises(PioneerUnavailableError):
        draft_reply(fake, TEXT, "Hardware", [])
    assert all(model != config.PIONEER_LLM for model, _ in fake.calls)


def test_guardrail_blocks_pii_and_passes_clean_text(metrics):
    """@spec:AC-035 @principle:P-012"""
    fake = FakeClient()
    assert privacy.guard(fake, "write to jane@example.org").found
    assert not privacy.guard(fake, "a specialist will call you").found
    assert fake.calls[0][0] == "fastino/gliguard-PII-multi"
    probe = metrics["hosted"]["guard_probe"]
    assert probe["com_pii"]["found"] is True
    assert probe["limpo"]["found"] is False


def test_guardrail_ignores_our_own_placeholders():
    """@spec:AC-035"""

    class PlaceholderEcho(FakeClient):
        def infer(self, model_id, text, schema):
            start = text.index("[PERSON]")
            return {
                "result": {
                    "entities": {
                        "person": [
                            {
                                "text": "[PERSON]",
                                "start": start,
                                "end": start + 8,
                                "confidence": 0.99,
                            }
                        ]
                    }
                }
            }

    assert not privacy.guard(PlaceholderEcho(), "Hello [PERSON], thanks").found


def test_guardrail_ignores_pronouns():
    """@spec:AC-035"""

    class PronounEcho(FakeClient):
        def infer(self, model_id, text, schema):
            return {
                "result": {
                    "entities": {
                        "person": [
                            {"text": "you", "start": 0, "end": 3, "confidence": 0.9},
                            {
                                "text": "Jane Roe",
                                "start": 8,
                                "end": 16,
                                "confidence": 0.99,
                            },
                        ]
                    }
                }
            }

    found = privacy.guard(PronounEcho(), "you and Jane Roe").entities
    assert [e["text"] for e in found] == ["Jane Roe"]
