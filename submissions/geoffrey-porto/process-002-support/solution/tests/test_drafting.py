"""Rascunho: sempre sugestão, nunca envio, sem vazar PII."""

from __future__ import annotations

import inspect

from fakes import FakeClient

from support_redesign import config, drafting, privacy

TEXT = privacy.with_customer_pii(
    "My tv is broken.", "Marisa Obrien", "carroll@example.com"
)


def test_draft_is_a_suggestion_with_context():
    """@spec:AC-036 @principle:P-004 @principle:P-012"""
    fake = FakeClient()
    d = drafting.draft_reply(fake, TEXT, "Hardware", ["old ticket about tv"])
    assert d.status == "requer_aprovacao"
    assert d.model == "deepseek-ai/DeepSeek-V4-Flash"
    assert d.queue == "Hardware"
    assert "[PERSON]" in d.masked_input
    assert d.guardrail_ok is True
    prompt = next(t for m, t in fake.calls if m == config.PIONEER_LLM)
    assert "Hardware" in prompt
    assert "old ticket about tv" in prompt


def test_draft_with_pii_is_flagged():
    """@spec:AC-036 @principle:P-013"""
    d = drafting.draft_reply(
        FakeClient(reply="Contact bob@example.com"), TEXT, "Hardware", []
    )
    assert d.guardrail_ok is False
    assert d.guardrail_entities


def test_no_code_path_sends_to_customer():
    """@spec:AC-036 @principle:P-004"""
    names = {n for n, _ in inspect.getmembers(drafting, inspect.isfunction)}
    assert not {
        n for n in names if any(w in n for w in ("send", "enviar", "reply_to", "post"))
    }
    source = inspect.getsource(drafting)
    assert "smtp" not in source.lower()


def test_real_drafts_do_not_leak_pii(metrics):
    """@spec:AC-037 @principle:P-013"""
    d = metrics["hosted"]["drafts"]
    assert d["n"] == config.DRAFT_SAMPLE_SIZE
    assert d["pii_leaks"] == 0
    assert d["all_require_approval"] is True
    assert d["empty_drafts"] == 0
    assert 0 <= d["guardrail_pass_rate"] <= 1
    assert d["median_client_ms"] > 0
    assert d["tokens_total"] > 0
    for ex in metrics["hosted"]["draft_examples"]:
        assert ex["status"] == "requer_aprovacao"
