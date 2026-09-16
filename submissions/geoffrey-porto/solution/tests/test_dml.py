"""Os três erros que fazem um intervalo de confiança mentir — e os testes deles."""

from __future__ import annotations

import numpy as np
import polars as pl
import pytest

from churn_diag.account_panel import build_account_panel
from churn_diag.dml import (
    OverlapError,
    cluster_robust_se,
    dml_effect,
    fold_of_each_group,
)
from churn_diag.loader import Tables
from churn_diag.pipeline import run_dml_use_cases

CONF = (("x",), ())
SEED = 7


def _panel(n_contas: int, linhas: int, efeito: float, correlacao: bool) -> pl.DataFrame:
    """Painel sintético: `correlacao` liga o ruído no nível da conta."""
    rng = np.random.default_rng(SEED)
    linhas_lista = []
    for c in range(n_contas):
        nivel = rng.normal(0, 1)
        d_conta = rng.integers(0, 2)
        for _ in range(linhas):
            x = rng.normal(0, 1)
            d = d_conta if correlacao else rng.integers(0, 2)
            base = nivel if correlacao else rng.normal(0, 1)
            linhas_lista.append(
                {
                    "account_id": f"A-{c}",
                    "x": x,
                    "d": int(d),
                    "y": efeito * d + 0.3 * x + base + rng.normal(0, 0.1),
                }
            )
    return pl.DataFrame(linhas_lista)


def test_cross_fitting_keeps_each_account_in_one_fold() -> None:
    """@spec:AC-035 — nenhuma conta aparece em duas partições do cross-fitting."""
    grupos = np.array([f"A-{i // 7}" for i in range(140)])
    folds = fold_of_each_group(grupos, n_splits=5)
    assert len(folds) == len(set(grupos))
    for conta in set(grupos):
        atribuidas = {folds[g] for g in {conta}}
        assert len(atribuidas) == 1


def test_overlap_is_always_reported() -> None:
    """@spec:AC-036 — mínimo, máximo e aparados saem sempre no resultado."""
    r = dml_effect(_panel(60, 5, 0.2, correlacao=False), "d", "y", CONF, caso="teste")
    assert 0.0 <= r.overlap_min <= r.overlap_max <= 1.0
    assert r.aparados >= 0
    assert r.n_contas == 60


def test_no_overlap_stops_with_a_clear_message() -> None:
    """@spec:AC-036 — tratamento previsível quase perfeitamente interrompe a estimativa."""
    rng = np.random.default_rng(SEED)
    linhas = []
    for c in range(60):
        for _ in range(5):
            x = rng.normal(0, 1)
            d = int(x > 0)  # tratamento determinado pelo confundidor: sem par
            linhas.append({"account_id": f"A-{c}", "x": x, "d": d, "y": 0.2 * d + x})
    with pytest.raises(OverlapError, match="sobreposição insuficiente"):
        dml_effect(pl.DataFrame(linhas), "d", "y", CONF, caso="sem_overlap")


def test_clustered_se_is_larger_when_rows_repeat_the_account() -> None:
    """@spec:AC-037 — correlação dentro da conta infla o erro-padrão agrupado."""
    r = dml_effect(
        _panel(40, 12, 0.2, correlacao=True), "d", "y", CONF, caso="agrupado"
    )
    assert r.se_cluster_pp > 1.5 * r.se_naive_pp


def test_clustered_and_naive_agree_when_rows_are_independent() -> None:
    """@spec:AC-037 — sem correlação, agrupado e ingênuo ficam próximos."""
    r = dml_effect(
        _panel(200, 1, 0.2, correlacao=False), "d", "y", CONF, caso="independente"
    )
    assert r.se_cluster_pp == pytest.approx(r.se_naive_pp, rel=0.3)


def test_cluster_se_formula_sums_inside_the_group_first() -> None:
    """@spec:AC-037 — a fórmula soma o score dentro da conta antes de elevar ao quadrado."""
    d_res = np.array([1.0, 1.0, -1.0, -1.0])
    u = np.array([1.0, 1.0, -1.0, -1.0])
    juntas = cluster_robust_se(d_res, u, np.array(["A", "A", "B", "B"]))
    separadas = cluster_robust_se(d_res, u, np.array(["A", "B", "C", "D"]))
    assert juntas > separadas


@pytest.fixture(scope="module")
def use_cases(real_tables: Tables) -> pl.DataFrame:
    """Roda os casos de uso uma vez só: cada estimativa custa 10 ajustes de modelo."""
    return run_dml_use_cases(build_account_panel(real_tables))


def test_use_cases_publish_effect_and_power(use_cases: pl.DataFrame) -> None:
    """@spec:AC-038 — efeito, intervalo, contas, tratados, eventos e efeito mínimo detectável."""
    out = use_cases
    assert {"cobranca_anual", "escalacao_suporte", "cobranca_anual_pos_quebra"} <= set(
        out["caso"]
    )
    for r in out.iter_rows(named=True):
        if r.get("theta_pp") is None:
            assert "não estimado" in r["leitura"]  # sobreposição insuficiente
            continue
        assert r["ci_low_pp"] <= r["theta_pp"] <= r["ci_high_pp"]
        assert r["mde_pp"] > 0
        assert r["n_contas"] > 0
        assert r["eventos_tratados"] >= 0
        cobre_zero = r["ci_low_pp"] <= 0 <= r["ci_high_pp"]
        assert r["significativo"] is not cobre_zero


def test_every_use_case_declares_how_it_handled_the_regime(
    use_cases: pl.DataFrame,
) -> None:
    """@spec:AC-039 — ou o regime entra no ajuste, ou a estimativa é restrita a um regime."""
    out = use_cases
    for r in out.iter_rows(named=True):
        tratamento = r["tratamento_do_regime"]
        assert tratamento in ("regime no ajuste", "restrito ao regime depois"), (
            tratamento
        )
