"""App: abre com dado real e a demo não escolhe a dedo."""

from __future__ import annotations

import os

import pytest
from conftest import free_addr
from streamlit.testing.v1 import AppTest

from support_redesign import router_bin
from support_redesign.config import SOLUTION_ROOT

APP = str(SOLUTION_ROOT / "app" / "streamlit_app.py")
TABS = ["Diagnóstico", "Roteador", "Fronteira IA × humano", "Similares", "ROI"]


APP_ROUTER_ADDR = free_addr()


@pytest.fixture(scope="module")
def app(metrics) -> AppTest:
    os.environ["ROUTER_ADDR"] = APP_ROUTER_ADDR
    at = AppTest.from_file(APP, default_timeout=180)
    at.run()
    yield at
    os.environ.pop("ROUTER_ADDR", None)
    router_bin.stop_started()


def test_all_sections_render_with_real_data(app):
    """@spec:AC-025"""
    assert not app.exception, [e.value for e in app.exception]
    assert [t.label for t in app.tabs] == TABS
    assert len(app.metric) >= 4


def test_demo_draws_a_holdout_ticket_and_shows_the_decision(app, metrics):
    """@spec:AC-026 @principle:P-004"""
    app.button(key="sortear").click().run()
    assert not app.exception, [e.value for e in app.exception]
    labels = {mt.label: mt.value for mt in app.metric}
    for label in ("Fila prevista", "Confiança", "Ação", "Fila verdadeira"):
        assert label in labels
    assert labels["Ação"] in {"AUTO", "CONFIRMAR", "HUMANO"}
    assert any("Motivo" in md.value for md in app.markdown)
    assert labels["Macro-F1 no hold-out"] == metrics["report"]["b0_macro_f1"]
    first = app.text_area(key="texto").value
    app.button(key="sortear").click().run()
    assert app.text_area(key="texto").value != first


def test_app_starts_the_router_by_itself(app):
    """@spec:AC-039"""
    assert router_bin.health(APP_ROUTER_ADDR)["status"] == "ok"
    assert any("Roteador Rust no ar" in c.value for c in app.caption)
    app.button(key="sortear").click().run()
    assert any("mesma decisão" in s.value for s in app.success)
