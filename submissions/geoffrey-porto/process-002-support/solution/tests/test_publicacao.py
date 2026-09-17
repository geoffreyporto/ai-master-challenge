"""Publicação: demo pública sem rascunho, bootstrap e página estática com números do pipeline."""

from __future__ import annotations

import json

import pytest
from streamlit.testing.v1 import AppTest

from support_redesign import bootstrap, public_page, router_bin
from support_redesign.config import ASSUMPTIONS_FILE, OUTPUTS_DIR, SOLUTION_ROOT
from support_redesign.roi import load_assumptions

APP = str(SOLUTION_ROOT / "app" / "streamlit_app.py")


def test_public_demo_never_offers_a_draft(metrics, monkeypatch):
    """@spec:AC-042 @principle:P-013"""
    from support_redesign import pioneer

    calls = []
    monkeypatch.setenv("SUPPORT_PUBLIC_DEMO", "1")
    monkeypatch.setattr(
        pioneer.PioneerClient, "__init__", lambda *a, **k: calls.append(1)
    )
    at = AppTest.from_file(APP, default_timeout=180)
    at.run()
    at.button(key="sortear").click().run()
    assert not at.exception, [e.value for e in at.exception]
    assert not [b for b in at.button if b.key == "rascunho"]
    assert any("Rascunho desligado na versão pública" in i.value for i in at.info)
    assert calls == []
    router_bin.stop_started()


def test_bootstrap_runs_pipeline_only_when_needed(tmp_path):
    """@spec:AC-043"""
    runs = []
    missing = (tmp_path / "a.json",)
    assert bootstrap.ensure_artifacts(lambda: runs.append(1), missing) is True
    assert runs == [1]
    missing[0].write_text("{}")
    assert bootstrap.ensure_artifacts(lambda: runs.append(1), missing) is False
    assert runs == [1]


def test_real_artifacts_are_complete_after_pipeline(metrics):
    """@spec:AC-043"""
    assert bootstrap.artifacts_ready()


def test_public_page_data_comes_from_metrics(metrics):
    """@spec:AC-045 @principle:P-003"""
    data = json.loads(public_page.PUBLIC_DATA.read_text())
    fresh = public_page.build(
        json.loads((OUTPUTS_DIR / "metrics.json").read_text()),
        load_assumptions(ASSUMPTIONS_FILE),
    )
    assert data == json.loads(json.dumps(fresh))
    assert data["report"] == metrics["report"]
    assert data["roi"]["coverage_auto"] == metrics["boundary"]["test"]["coverage_auto"]


def test_public_page_renders_data_as_text_only():
    """@spec:AC-045 @principle:P-009"""
    html = (public_page.PUBLIC_DATA.parent / "index.html").read_text()
    assert "innerHTML" not in html
    assert 'fetch("data.json")' in html
    assert "/api/route" in html
    assert "pio_" not in html


@pytest.mark.parametrize("path", ["router/vercel.json", "router/.vercelignore"])
def test_vercel_config_exists(path):
    """@spec:AC-044"""
    assert (SOLUTION_ROOT / path).is_file()


def test_offline_pipeline_never_creates_a_pioneer_client(monkeypatch):
    """@spec:AC-043 @principle:P-013"""
    from support_redesign import hosted_eval, pioneer

    monkeypatch.setattr(
        pioneer.PioneerClient, "__init__", lambda *a, **k: pytest.fail("rede chamada")
    )
    with pytest.raises(hosted_eval.HostedCacheIncompleteError):
        hosted_eval.LazyClient(offline=True)()


def test_default_bootstrap_uses_the_light_serving_build(monkeypatch, tmp_path):
    """@spec:AC-043"""
    from support_redesign import pipeline

    called = []
    monkeypatch.setattr(pipeline, "build_serving", lambda: called.append("serving"))
    monkeypatch.setattr(pipeline, "run", lambda *a, **k: called.append("run"))
    assert bootstrap.ensure_artifacts(required=(tmp_path / "x",)) is True
    assert called == ["serving"]


def test_serving_build_matches_the_full_pipeline(metrics):
    """@spec:AC-043 @principle:P-006"""
    import pickle

    from support_redesign import pipeline

    with (pipeline.MODELS_DIR / "b0.pkl").open("rb") as fh:
        full = pickle.load(fh)  # noqa: S301 — artefato do próprio pipeline
    pipeline.build_serving()
    with (pipeline.MODELS_DIR / "b0.pkl").open("rb") as fh:
        light = pickle.load(fh)  # noqa: S301
    assert light["policy"] == full["policy"]
