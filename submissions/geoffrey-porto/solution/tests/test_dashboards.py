"""Painéis: o teste existe para impedir o erro clássico de dashboard.

Dois erros, na verdade. O primeiro é o número que só existe na tela — aqui todo
KPI com chave declarada é conferido contra o pipeline. O segundo é o KPI
inventado para não deixar o quadrante vazio: CAC, LTV e verba de mídia não estão
no dataset, e o teste garante que eles continuem ausentes.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from churn_diag.config import CS_TOP_N, SOLUTION_ROOT
from churn_diag.dashboards import (
    NIVEIS,
    STAKEHOLDERS,
    base_por_canal,
    build_payload,
    carga_de_suporte,
    features_com_erro,
    mrr_por_plano,
    receita_mensal,
    write_payload,
)
from churn_diag.loader import Tables
from churn_diag.pipeline import Result, analyse

DATA_JS = SOLUTION_ROOT / "dashboard" / "data.js"
PAGINA = SOLUTION_ROOT / "dashboard" / "index.html"
APP = SOLUTION_ROOT / "dashboard" / "app.js"
PROIBIDOS = ("cac", "ltv", "roas", "verba", "login")


@pytest.fixture(scope="module")
def resultado(real_tables: Tables) -> Result:
    return analyse(real_tables, CS_TOP_N)


@pytest.fixture(scope="module")
def payload(real_tables: Tables, resultado: Result) -> dict:
    return build_payload(real_tables, resultado.report, resultado.tables)


def test_os_cinco_paineis_tem_os_quatro_niveis(payload: dict) -> None:
    """@spec:AC-044"""
    assert set(payload["paineis"]) == set(STAKEHOLDERS)
    for nome, painel in payload["paineis"].items():
        for nivel in NIVEIS:
            secao = painel[nivel]
            tem_dados = bool(secao["dados"]) or bool(secao.get("acoes"))
            assert tem_dados, f"{nome}/{nivel} sem dados e sem ações"
            assert secao["leitura"].strip(), f"{nome}/{nivel} sem leitura"
            assert secao["titulo"].strip()


def test_todo_kpi_com_chave_bate_com_o_pipeline(
    payload: dict, resultado: Result
) -> None:
    """@spec:AC-045 @principle:P-003"""
    conferidos = 0
    for nome, painel in payload["paineis"].items():
        assert len(painel["kpis"]) >= 4, f"{nome} deveria ter ao menos 4 KPIs"
        for kpi in painel["kpis"]:
            if not kpi["chave"]:
                continue
            assert kpi["chave"] in resultado.report, (
                f"{nome}: chave inexistente no pipeline: {kpi['chave']}"
            )
            assert kpi["valor"] == pytest.approx(resultado.report[kpi["chave"]]), (
                f"{nome}/{kpi['rotulo']}: painel {kpi['valor']} ≠ pipeline "
                f"{resultado.report[kpi['chave']]}"
            )
            conferidos += 1
    assert conferidos >= 15, "quase todo KPI do painel deveria ser rastreável"


def test_cada_painel_declara_o_que_nao_consegue_mostrar(payload: dict) -> None:
    """@spec:AC-046"""
    for nome, painel in payload["paineis"].items():
        assert painel["lacunas"], f"{nome} não declarou nenhuma lacuna"
        for lacuna in painel["lacunas"]:
            assert lacuna["kpi"].strip()
            assert lacuna["porque"].strip()


def test_kpi_impossivel_nao_vira_numero(payload: dict) -> None:
    """@spec:AC-046"""
    for nome, painel in payload["paineis"].items():
        rotulos = " ".join(k["rotulo"].lower() for k in painel["kpis"])
        for proibido in PROIBIDOS:
            assert proibido not in rotulos, (
                f"{nome} exibe '{proibido}' como KPI — o dataset não sustenta isso"
            )


def test_a_serie_do_painel_e_a_mesma_do_relatorio(
    real_tables: Tables, resultado: Result
) -> None:
    """@spec:AC-047 @principle:P-003"""
    serie = receita_mensal(real_tables)
    dezembro = serie.filter(serie["month"] == serie["month"].max())
    assert float(dezembro["mrr_churn_pct"][0]) == pytest.approx(
        resultado.report["mrr_churn_dec24_pct"], abs=0.01
    )


def test_agregados_cobrem_as_dimensoes_do_negocio(real_tables: Tables) -> None:
    """@spec:AC-044"""
    assert mrr_por_plano(real_tables).height == 3
    canais = base_por_canal(real_tables)
    assert canais.height == 5
    assert canais["mrr_ativo"].sum() > 0
    assert carga_de_suporte(real_tables).height == 4
    assert features_com_erro(real_tables, top_n=6).height == 6


def test_payload_gravado_abre_sem_servidor(payload: dict, tmp_path: Path) -> None:
    """@spec:AC-044"""
    destino = write_payload(payload, tmp_path / "data.js")
    texto = destino.read_text(encoding="utf-8")
    assert texto.startswith("window.DASHBOARD_DATA = ")
    corpo = json.loads(texto[len("window.DASHBOARD_DATA = ") : texto.rindex(";")])
    assert set(corpo["paineis"]) == set(STAKEHOLDERS)


def test_a_pagina_publicada_esta_em_dia(payload: dict) -> None:
    """@spec:AC-044"""
    """A página versionada precisa ter sido gerada, compilada e vendorizada."""
    assert PAGINA.exists(), "index.html sumiu"
    assert APP.exists(), "rode `tsc -p dashboard/tsconfig.json`"
    assert DATA_JS.exists(), "rode `uv run python -m churn_diag`"
    html = PAGINA.read_text(encoding="utf-8")
    for recurso in (
        "vendor/d3.v7.min.js",
        "vendor/tailwind-play.js",
        "data.js",
        "app.js",
    ):
        assert recurso in html, f"index.html não carrega {recurso}"
        if recurso.startswith("vendor/"):
            assert (SOLUTION_ROOT / "dashboard" / recurso).exists(), (
                f"{recurso} não foi vendorizado"
            )
    publicado = DATA_JS.read_text(encoding="utf-8")
    corpo = json.loads(
        publicado[len("window.DASHBOARD_DATA = ") : publicado.rindex(";")]
    )
    assert corpo["paineis"]["ceo"]["kpis"] == payload["paineis"]["ceo"]["kpis"], (
        "dashboard/data.js desatualizado: rode `uv run python -m churn_diag`"
    )
