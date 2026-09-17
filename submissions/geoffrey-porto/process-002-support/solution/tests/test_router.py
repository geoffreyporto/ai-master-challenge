"""Roteador Rust: a prova do cargo entra no mesmo TAP do onp-spec."""

from __future__ import annotations

import json
import shutil
import subprocess

import pytest

from support_redesign.config import SOLUTION_ROOT
from support_redesign.pipeline import GOLDEN_FILE, ROUTER_MODEL

ROUTER = SOLUTION_ROOT / "router"


def _cargo(*args: str) -> subprocess.CompletedProcess[str]:
    if shutil.which("cargo") is None:
        pytest.fail("cargo não encontrado: instale Rust 1.98.1 (rustup)")
    return subprocess.run(
        ["cargo", *args],
        cwd=ROUTER,
        capture_output=True,
        text=True,
        timeout=900,
        check=False,
    )


@pytest.fixture(scope="module")
def cargo_tests(metrics) -> str:
    out = _cargo("test", "--release", "--", "--nocapture")
    assert out.returncode == 0, out.stdout[-3000:] + out.stderr[-3000:]
    return out.stdout + out.stderr


def test_exported_model_and_golden_match_the_pipeline(metrics):
    """@spec:AC-028"""
    model = json.loads(ROUTER_MODEL.read_text())
    assert model["policy"] == json.loads(json.dumps(metrics["boundary"]["policy"]))
    lines = GOLDEN_FILE.read_text().splitlines()
    assert len(lines) == metrics["split"]["test"]


def test_router_answers_topic_confidence_and_action(cargo_tests):
    """@spec:AC-027"""
    assert "route_returns_topic_confidence_and_action ... ok" in cargo_tests
    assert "health_is_ok ... ok" in cargo_tests
    assert "critical_priority_never_goes_straight_to_auto ... ok" in cargo_tests


def test_rust_decides_like_python_on_full_holdout(cargo_tests, metrics):
    """@spec:AC-028 @principle:P-005"""
    assert "rust_matches_python_on_full_holdout ... ok" in cargo_tests
    assert f"paridade: {metrics['split']['test']} tickets" in cargo_tests
    assert "normalize_matches_python_rules ... ok" in cargo_tests


def test_router_rejects_bad_input_and_keeps_serving(cargo_tests):
    """@spec:AC-029"""
    assert "rejects_invalid_input_and_keeps_serving ... ok" in cargo_tests


def test_router_passes_strict_lints():
    """@principle:P-011"""
    out = _cargo("clippy", "--release", "--all-targets", "--", "-D", "warnings")
    assert out.returncode == 0, out.stderr[-3000:]
