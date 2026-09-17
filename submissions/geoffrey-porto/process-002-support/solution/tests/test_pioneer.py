"""Transporte Pioneer: a chave nunca vaza e o 503 de aquecimento é tratado."""

from __future__ import annotations

import httpx
import pytest

from support_redesign import pioneer


def test_key_comes_only_from_environment(monkeypatch, tmp_path):
    """@principle:P-009"""
    monkeypatch.delenv("PIONEER_API_KEY", raising=False)
    monkeypatch.delenv("PIONEER_ENV_FILE", raising=False)
    missing = tmp_path / "nao-existe.env"
    with pytest.raises(pioneer.PioneerKeyMissingError) as err:
        pioneer.load_key(missing)
    default = tmp_path / "default.env"
    default.write_text("PIONEER_API_KEY=from_default_file\n")
    assert pioneer.load_key(default) == "from_default_file"
    env = tmp_path / ".env"
    env.write_text("OTHER=1\nPIONEER_API_KEY: fake_value_123\n")
    monkeypatch.setenv("PIONEER_ENV_FILE", str(env))
    assert pioneer.load_key(default) == "fake_value_123"
    assert "fake_value_123" not in str(err.value)


def test_default_env_file_is_never_versioned():
    """@principle:P-009"""
    import subprocess

    from support_redesign.config import SOLUTION_ROOT

    assert ".env" in (SOLUTION_ROOT / ".gitignore").read_text().split()
    tracked = subprocess.run(
        ["git", "ls-files", "--", str(pioneer.DEFAULT_ENV_FILE)],
        capture_output=True,
        text=True,
        check=False,
        cwd=SOLUTION_ROOT,
    ).stdout
    assert tracked.strip() == ""


def _client(handler) -> pioneer.PioneerClient:
    c = pioneer.PioneerClient(key="k", retries=3)
    c._http = httpx.Client(
        base_url=pioneer.BASE_URL, transport=httpx.MockTransport(handler)
    )
    return c


def test_cold_start_503_is_retried_then_succeeds():
    """@spec:AC-030"""
    calls = []

    def handler(request):
        calls.append(request)
        if len(calls) == 1:
            return httpx.Response(503, headers={"retry-after": "0"})
        return httpx.Response(200, json={"result": {}, "model_used": "m"})

    out = _client(handler).infer("m", "t", {"entities": ["x"]})
    assert out["model_used"] == "m"
    assert len(calls) == 2
    assert b'"store":false' in calls[0].content.replace(b" ", b"")


def test_persistent_503_raises_unavailable():
    """@spec:AC-030"""
    with pytest.raises(pioneer.PioneerUnavailableError):
        _client(lambda r: httpx.Response(503, headers={"retry-after": "0"})).infer(
            "m", "t", {}
        )


def test_run_cached_only_calls_missing_items(tmp_path):
    """@spec:AC-030"""
    seen = []
    cache = tmp_path / "c.json"
    pioneer.run_cached([("a", 1)], lambda v: seen.append(v) or {"v": v}, cache)
    out = pioneer.run_cached(
        [("a", 1), ("b", 2)], lambda v: seen.append(v) or {"v": v}, cache
    )
    assert seen == [1, 2]
    assert out == {"a": {"v": 1}, "b": {"v": 2}}
