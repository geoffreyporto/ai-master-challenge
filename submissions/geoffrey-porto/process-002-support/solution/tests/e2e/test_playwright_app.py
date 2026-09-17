"""E2E no Chrome real: o avaliador vê o fluxo funcionando e as capturas viram evidência."""

from __future__ import annotations

import os
import re
import subprocess
import sys
import time
import urllib.request

import pytest
from conftest import free_addr
from playwright.sync_api import Page, expect, sync_playwright

from support_redesign import pioneer
from support_redesign.config import SOLUTION_ROOT

SHOTS = SOLUTION_ROOT.parent / "process-log" / "screenshots"
BOOT_S = 120
DRAFT_S = 180


def _wait_http(url: str, timeout: float) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2):  # noqa: S310 — localhost
                return
        except OSError:
            time.sleep(0.5)
    pytest.fail(f"{url} não respondeu em {timeout}s")


@pytest.fixture(scope="module")
def server(metrics):
    app_addr, router_addr = free_addr(), free_addr()
    port = app_addr.rsplit(":", 1)[1]
    env = {**os.environ, "ROUTER_ADDR": router_addr}
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            "app/streamlit_app.py",
            "--server.port",
            port,
            "--server.headless",
            "true",
            "--browser.gatherUsageStats",
            "false",
        ],
        cwd=SOLUTION_ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        _wait_http(f"http://{app_addr}/_stcore/health", BOOT_S)
        yield {"url": f"http://{app_addr}", "router": router_addr}
    finally:
        proc.terminate()
        proc.wait(timeout=20)
        subprocess.run(["pkill", "-f", f"--addr {router_addr}"], check=False)


@pytest.fixture(scope="module")
def page(server):
    SHOTS.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        pg = browser.new_page(viewport={"width": 1440, "height": 1000})
        pg.set_default_timeout(BOOT_S * 1000)
        pg.goto(server["url"])
        expect(
            pg.get_by_text("Redesign de Suporte — onde perdemos tempo")
        ).to_be_visible()
        yield pg
        browser.close()


def _tab(page: Page, name: str):
    page.get_by_role("tab", name=name).click()
    return page.get_by_role("tabpanel").filter(visible=True)


def _shot(page: Page, name: str) -> None:
    page.wait_for_timeout(800)
    page.screenshot(path=SHOTS / name, full_page=True)
    assert (SHOTS / name).stat().st_size > 10_000


def _closed_count(panel) -> int:
    text = panel.get_by_text(re.compile(r"tickets fechados no filtro")).inner_text()
    return int(re.search(r"(\d+)", text).group(1))


def test_kpis_tabs_and_router_status(page, server, metrics):
    """@spec:AC-040 @principle:P-003"""
    rep = metrics["report"]
    for tab in ("Diagnóstico", "Roteador", "Fronteira IA × humano", "Similares", "ROI"):
        expect(page.get_by_role("tab", name=tab)).to_be_visible()
    metrics_row = page.locator('[data-testid="stMetric"]').filter(visible=True)
    expect(metrics_row.first).to_contain_text(rep["b0_macro_f1"])
    expect(page.get_by_text("Roteador Rust no ar")).to_be_visible()
    _shot(page, "e2e-01-visao-geral.png")


def test_channel_filter_changes_the_count(page):
    """@spec:AC-040"""
    panel = _tab(page, "Diagnóstico")
    before = _closed_count(panel)
    panel.locator('[data-testid="stMultiSelect"]').first.click()
    page.get_by_role("option", name="Email").click()
    page.keyboard.press("Escape")
    expect(
        panel.get_by_text(re.compile(r"tickets fechados no filtro"))
    ).not_to_contain_text(f"{before} tickets")
    after = _closed_count(panel)
    assert 0 < after < before
    _shot(page, "e2e-02-diagnostico-filtro.png")


def test_drawn_ticket_gets_decision_and_rust_agrees(page):
    """@spec:AC-040 @spec:AC-026 @principle:P-005"""
    panel = _tab(page, "Roteador")
    panel.get_by_role("button", name="Sortear ticket do hold-out").click()
    expect(panel.get_by_text("Fila verdadeira")).to_be_visible()
    expect(panel.get_by_text("Motivo:")).to_be_visible()
    expect(
        panel.get_by_text(re.compile(r"Roteador Rust .*mesma decisão"))
    ).to_be_visible()
    action = panel.locator('[data-testid="stMetric"]').filter(has_text="Ação")
    expect(action).to_contain_text(re.compile(r"AUTO|CONFIRMAR|HUMANO"))
    _shot(page, "e2e-03-roteador-ticket-sorteado.png")


def test_critical_priority_is_never_automatic(page):
    """@spec:AC-040 @principle:P-004"""
    panel = _tab(page, "Roteador")
    panel.locator('[data-testid="stSelectbox"]').click()
    page.get_by_role("option", name="Critical").click()
    action = panel.locator('[data-testid="stMetric"]').filter(has_text="Ação")
    expect(action).to_contain_text(re.compile(r"CONFIRMAR|HUMANO"))
    expect(panel.get_by_text(re.compile(r"mesma decisão"))).to_be_visible()
    _shot(page, "e2e-04-roteador-critical.png")


def test_draft_or_missing_key_notice(page):
    """@spec:AC-041 @principle:P-013"""
    panel = _tab(page, "Roteador")
    panel.get_by_role("button", name="Gerar rascunho").click()
    try:
        pioneer.load_key()
    except pioneer.PioneerKeyMissingError:
        expect(panel.get_by_text("Sem chave do Pioneer")).to_be_visible()
        _shot(page, "e2e-05-rascunho-sem-chave.png")
        return
    expect(panel.get_by_text("Guardrail de PII")).to_be_visible(timeout=DRAFT_S * 1000)
    expect(panel.get_by_text("Enviado ao LLM (mascarado)")).to_be_visible()
    expect(panel.get_by_text("Rascunho — requer aprovação do agente")).to_be_visible()
    _shot(page, "e2e-05-rascunho-pioneer.png")


def test_boundary_tab_shows_measured_policy(page, metrics):
    """@spec:AC-040"""
    panel = _tab(page, "Fronteira IA × humano")
    expect(panel.get_by_text("Onde a IA para e o humano assume")).to_be_visible()
    expect(panel.get_by_text(re.compile(r"Segunda opinião GLiNER2"))).to_be_visible()
    expect(panel.get_by_text(re.compile("desligada"))).to_be_visible()
    _shot(page, "e2e-06-fronteira.png")


def test_similar_ticket_search(page):
    """@spec:AC-040"""
    panel = _tab(page, "Similares")
    box = panel.get_by_label("Buscar")
    box.fill("printer toner replacement needed on third floor")
    box.press("Enter")
    grid = panel.locator('[data-testid="stDataFrame"]').last
    expect(grid).to_be_visible()
    _shot(page, "e2e-07-similares.png")


def test_changing_an_assumption_changes_roi(page):
    """@spec:AC-040 @spec:AC-024"""
    panel = _tab(page, "ROI")
    saving = panel.locator('[data-testid="stMetric"]').filter(
        has_text="Economia líquida/ano"
    )
    before = saving.inner_text()
    volume = panel.get_by_label("Tickets/ano")
    volume.fill("60000")
    volume.press("Enter")
    expect(saving).not_to_have_text(before)
    _shot(page, "e2e-08-roi-premissas.png")
