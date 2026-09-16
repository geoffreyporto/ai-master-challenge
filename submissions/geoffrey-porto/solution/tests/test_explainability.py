"""Explicabilidade: o gráfico só vale se a conta fechar.

Aqui o teste central não é estético. Valores de Shapley aproximados (o que a
`shap` faz para modelos genéricos) podem somar diferente da previsão; os exatos
não podem. Se a soma não bater, o gráfico está contando uma história que o
modelo não contou.
"""

from __future__ import annotations

import numpy as np
import polars as pl
import pytest

from churn_diag.dml import cate_quantiles
from churn_diag.explainability import (
    AUDIT_FEATURES,
    arrays_from_tidy,
    beeswarm,
    cate_staircase,
    dependence,
    environment_heatmap,
    exact_shapley_values,
    run_audit,
    score_contributions,
    shapley_frame,
    tidy_shapley,
    waterfall,
)

SEED = 11
NOMES = ("a", "b", "ignorada")


def _dados(n: int = 60) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(SEED)
    x = rng.normal(0, 1, size=(n, 3))
    fundo = rng.normal(0, 1, size=(25, 3))
    return x, fundo


def _modelo(a: np.ndarray) -> np.ndarray:
    """Usa só as duas primeiras colunas — a terceira é ignorada de propósito."""
    return 1 / (1 + np.exp(-(0.8 * a[:, 0] + 1.3 * a[:, 1] * (a[:, 0] > 0))))


# @spec:AC-040
def test_shapley_exato_fecha_a_conta() -> None:
    x, fundo = _dados()
    phi, base = exact_shapley_values(_modelo, x, fundo)
    erro = np.abs(phi.sum(axis=1) + base - _modelo(x)).max()
    assert erro < 1e-10, f"eficiência violada: {erro}"


# @spec:AC-040
def test_variavel_ignorada_recebe_zero() -> None:
    x, fundo = _dados()
    phi, _ = exact_shapley_values(_modelo, x, fundo)
    assert np.abs(phi[:, 2]).max() < 1e-12
    assert np.abs(phi[:, 1]).mean() > 1e-3


# @spec:AC-040
def test_recusa_muitas_variaveis() -> None:
    rng = np.random.default_rng(SEED)
    grande = rng.normal(size=(3, 13))
    with pytest.raises(ValueError, match="exato"):
        exact_shapley_values(_modelo, grande, grande)


# @spec:AC-041
def test_tabela_de_apoio_traz_variacao_entre_ambientes() -> None:
    x, fundo = _dados()
    phi, _ = exact_shapley_values(_modelo, x, fundo)
    envs = np.array(["norte", "sul"] * (len(x) // 2))
    frame = shapley_frame(phi, x, NOMES, envs)
    assert frame.columns[:2] == ["feature", "mean_abs_shapley"]
    assert {"env_norte", "env_sul", "std_entre_ambientes", "troca_de_sinal"} <= set(
        frame.columns
    )
    assert frame["mean_abs_shapley"].is_sorted(descending=True)
    assert (
        frame.filter(pl.col("feature") == "ignorada")["std_entre_ambientes"][0] == 0.0
    )


# @spec:AC-041
def test_os_cinco_graficos_saem(tmp_path) -> None:
    x, fundo = _dados()
    phi, base = exact_shapley_values(_modelo, x, fundo)
    envs = np.array(["norte", "sul"] * (len(x) // 2))
    frame = shapley_frame(phi, x, NOMES, envs)
    quantis = pl.DataFrame(
        {
            "quantil": ["Q1", "Q2"],
            "efeito_medio": [-0.01, 0.02],
            "erro_padrao": [0.01, 0.01],
        }
    )
    saidas = [
        beeswarm(phi, x, NOMES, tmp_path / "bee.png"),
        dependence(
            phi, x, NOMES, feature="a", interaction="b", path=tmp_path / "dep.png"
        ),
        waterfall(phi[0], x[0], NOMES, base=base, path=tmp_path / "wat.png"),
        environment_heatmap(frame, tmp_path / "heat.png"),
        cate_staircase(quantis, tmp_path / "esc.png"),
    ]
    assert len(saidas) == 5
    assert all(p.exists() and p.stat().st_size > 1000 for p in saidas)


# @spec:AC-041
def test_forma_longa_ida_e_volta() -> None:
    x, fundo = _dados()
    phi, _ = exact_shapley_values(_modelo, x, fundo)
    envs = np.array(["norte", "sul"] * (len(x) // 2))
    from churn_diag.explainability import AuditArtifacts

    art = AuditArtifacts(
        phi=phi,
        x=x,
        names=NOMES,
        base=0.5,
        envs=envs,
        frame=shapley_frame(phi, x, NOMES, envs),
        audit_roc=0.5,
        efficiency_error=0.0,
        top_row=0,
    )
    phi2, x2, nomes2, envs2 = arrays_from_tidy(tidy_shapley(art))
    assert nomes2 == NOMES
    assert np.allclose(phi2, phi)
    assert np.allclose(x2, x)
    assert list(envs2) == list(envs)


def _painel_cate(efeito_heterogeneo: bool, n_contas: int = 260) -> pl.DataFrame:
    rng = np.random.default_rng(SEED)
    linhas = []
    for c in range(n_contas):
        x = rng.normal(0, 1)
        for _ in range(3):
            d = int(rng.random() < 1 / (1 + np.exp(-0.5 * x)))
            tau = 1.5 * x if efeito_heterogeneo else 0.0
            y = tau * d + 0.4 * x + rng.normal(0, 0.3)
            linhas.append({"account_id": f"A-{c}", "x": x, "d": d, "y": y})
    return pl.DataFrame(linhas)


# @spec:AC-042
def test_escada_inclina_quando_ha_heterogeneidade() -> None:
    q = cate_quantiles(_painel_cate(True), "d", "y", (("x",), ()), n_quantis=4)
    assert q.height == 4
    assert q["efeito_medio"][-1] - q["efeito_medio"][0] > 1.0
    assert bool(q["heterogeneidade"][0])


# @spec:AC-042
def test_escada_fica_plana_quando_o_efeito_e_nulo() -> None:
    q = cate_quantiles(_painel_cate(False), "d", "y", (("x",), ()), n_quantis=4)
    assert abs(q["spread"][0]) < 0.5
    assert not bool(q["heterogeneidade"][0])


# @spec:AC-043
def test_explicacao_do_score_soma_exatamente_a_perda(real_tables) -> None:
    from churn_diag.metrics import exposure_panel
    from churn_diag.risk import (
        cs_priority_list,
        monthly_hazard_by_age,
        subscription_risk,
    )

    risco = subscription_risk(
        real_tables, monthly_hazard_by_age(exposure_panel(real_tables.subscriptions))
    )
    cs = cs_priority_list(real_tables, risco, top_n=5)
    conta = cs["account_id"][0]
    linhas = score_contributions(risco, conta)
    assert linhas.height >= 1
    assert set(linhas.columns) >= {"subscription_id", "age_days", "mrr", "risco_90d"}
    # `expected_loss_90d` da lista do CS é a mesma soma, arredondada ao real.
    assert linhas["contribuicao"].sum() == pytest.approx(
        cs.filter(pl.col("account_id") == conta)["expected_loss_90d"][0], abs=0.5
    )
    assert linhas["contribuicao"].is_sorted(descending=True)


# @spec:AC-041
def test_auditoria_no_painel_real(real_tables) -> None:
    art = run_audit(real_tables, n_rows=24)
    assert art.phi.shape == (24, len(AUDIT_FEATURES))
    assert art.efficiency_error < 1e-10
    assert 0.3 < art.audit_roc < 0.7, (
        "o modelo de auditoria deveria empatar com o acaso fora do tempo"
    )
    assert art.frame.height == len(AUDIT_FEATURES)
