"""Double Machine Learning com cross-fitting agrupado e erro-padrão agrupado.

Três defeitos comuns em DML sobre painel de contas — e o que este módulo faz:

1. **Cross-fitting que mistura a conta.** Com snapshots mensais, `KFold`
   embaralhado põe a mesma conta em treino e validação: as funções auxiliares
   decoram a conta e o resíduo deixa de ser ortogonal. Aqui o corte é por conta
   (`GroupKFold`).
2. **Erro-padrão ingênuo.** Linhas da mesma conta não são independentes (ICC do
   churn ≈ 0,36 neste painel). O erro-padrão é sanduíche **agrupado por conta**.
3. **Sobreposição não verificada.** Comparar tratados sem par controle não é
   estimar efeito. A checagem é obrigatória, com aparo e contagem.

O modelo é parcialmente linear: Y = θ·D + g(X) + ε. Com Y binário, θ é a
variação em **pontos percentuais** na probabilidade de churn.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
import polars as pl
from scipy import stats
from sklearn.ensemble import (
    HistGradientBoostingClassifier,
    HistGradientBoostingRegressor,
)
from sklearn.model_selection import GroupKFold

from churn_diag.config import SEED
from churn_diag.screening import build_matrix

TRIM_BOUNDS: tuple[float, float] = (0.02, 0.98)
MIN_EFFECTIVE_ROWS: int = 30
MAX_TRIMMED_SHARE: float = 0.5
POWER_Z: float = 2.802  # z(0,975) + z(0,80): efeito mínimo detectável a 80%


class OverlapError(ValueError):
    """Tratamento previsível demais: não há par comparável para estimar efeito."""


@dataclass(frozen=True, slots=True)
class DmlResult:
    """Efeito estimado + tudo que é preciso para julgar se ele vale alguma coisa."""

    caso: str
    tratamento: str
    desfecho: str
    theta_pp: float
    ci_low_pp: float
    ci_high_pp: float
    p_value: float
    se_cluster_pp: float
    se_naive_pp: float
    mde_pp: float
    n: int
    n_contas: int
    n_tratados: int
    eventos_tratados: int
    overlap_min: float
    overlap_max: float
    aparados: int
    significativo: bool
    leitura: str

    def as_row(self) -> dict[str, object]:
        return asdict(self)


def _cross_fitted_residuals(
    x: np.ndarray, d: np.ndarray, y: np.ndarray, groups: np.ndarray, n_splits: int
) -> tuple[np.ndarray, np.ndarray]:
    """Resíduos fora da amostra, com as partições cortadas POR CONTA (AC-035)."""
    m_hat = np.zeros(len(d))
    g_hat = np.zeros(len(y))
    n_splits = min(n_splits, len(np.unique(groups)))
    for fit_idx, pred_idx in GroupKFold(n_splits=n_splits).split(x, y, groups):
        tratamento = HistGradientBoostingClassifier(
            max_depth=3, learning_rate=0.05, max_iter=200, random_state=SEED
        ).fit(x[fit_idx], d[fit_idx])
        m_hat[pred_idx] = tratamento.predict_proba(x[pred_idx])[:, 1]
        desfecho = HistGradientBoostingRegressor(
            max_depth=3, learning_rate=0.05, max_iter=200, random_state=SEED
        ).fit(x[fit_idx], y[fit_idx])
        g_hat[pred_idx] = desfecho.predict(x[pred_idx])
    return m_hat, g_hat


def fold_of_each_group(groups: np.ndarray, n_splits: int) -> dict[str, int]:
    """Partição de cada conta — usado pelo teste que prova o agrupamento."""
    folds: dict[str, int] = {}
    n_splits = min(n_splits, len(np.unique(groups)))
    x = np.zeros((len(groups), 1))
    for fold, (_, pred_idx) in enumerate(
        GroupKFold(n_splits=n_splits).split(x, x[:, 0], groups)
    ):
        for g in np.unique(groups[pred_idx]):
            folds[g] = fold
    return folds


def cluster_robust_se(
    d_res: np.ndarray, u_hat: np.ndarray, groups: np.ndarray
) -> float:
    """Erro-padrão sanduíche agrupado: soma dentro da conta antes de elevar ao quadrado."""
    scores = d_res * u_hat
    soma_por_grupo = {}
    for g, s in zip(groups, scores, strict=True):
        soma_por_grupo[g] = soma_por_grupo.get(g, 0.0) + s
    meat = sum(v**2 for v in soma_por_grupo.values())
    bread = float((d_res**2).sum())
    return float(np.sqrt(meat) / bread) if bread > 0 else float("nan")


def dml_effect(
    panel: pl.DataFrame,
    treatment: str,
    outcome: str,
    confounders: tuple[tuple[str, ...], tuple[str, ...]],
    *,
    caso: str = "",
    cluster: str = "account_id",
    n_splits: int = 5,
    trim: tuple[float, float] = TRIM_BOUNDS,
) -> DmlResult:
    """Efeito causal de `treatment` sobre `outcome`, em pontos percentuais.

    `confounders` é (numéricos, categóricos) — só variáveis anteriores ao
    tratamento. A sobreposição é sempre checada (AC-036) e o erro-padrão é
    sempre agrupado por `cluster` (AC-037).
    """
    numeric, categorical = confounders
    dados = panel.drop_nulls([treatment, outcome, cluster, *categorical])
    x, _ = build_matrix(dados, list(numeric), list(categorical))
    d = dados[treatment].cast(pl.Float64).to_numpy()
    y = dados[outcome].cast(pl.Float64).to_numpy()
    groups = dados[cluster].to_numpy()

    m_hat, g_hat = _cross_fitted_residuals(x, d, y, groups, n_splits)

    # --- sobreposição (AC-036): sem par comparável, não há efeito a estimar
    dentro = (m_hat >= trim[0]) & (m_hat <= trim[1])
    aparados = int((~dentro).sum())
    if aparados > MAX_TRIMMED_SHARE * len(d) or int(dentro.sum()) < MIN_EFFECTIVE_ROWS:
        raise OverlapError(
            f"sobreposição insuficiente em '{caso or treatment}': "
            f"{aparados} de {len(d)} linhas fora de [{trim[0]}, {trim[1]}] "
            f"(probabilidade de tratamento entre {m_hat.min():.3f} e {m_hat.max():.3f}). "
            "Tratados e controles não são comparáveis — reveja a população ou o tratamento."
        )

    d_res = (d - m_hat)[dentro]
    y_res = (y - g_hat)[dentro]
    grupos_validos = groups[dentro]
    theta = float((d_res * y_res).sum() / (d_res**2).sum())
    u_hat = y_res - theta * d_res
    se = cluster_robust_se(d_res, u_hat, grupos_validos)
    se_naive = float(
        np.sqrt(np.mean(d_res**2 * u_hat**2) / (np.mean(d_res**2) ** 2 * len(d_res)))
    )
    p_value = float(2 * stats.norm.sf(abs(theta / se))) if se > 0 else float("nan")
    ci = (theta - 1.96 * se, theta + 1.96 * se)
    significativo = bool(ci[0] > 0 or ci[1] < 0)
    mde = POWER_Z * se
    tratados = dados.filter(pl.col(treatment) > 0)
    leitura = (
        f"efeito de {100 * theta:+.2f} pp (IC {100 * ci[0]:+.2f} a {100 * ci[1]:+.2f})"
        if significativo
        else (
            f"sem efeito detectável; o desenho só enxergaria diferenças de "
            f"{100 * mde:.1f} pp ou mais"
        )
    )
    return DmlResult(
        caso=caso or treatment,
        tratamento=treatment,
        desfecho=outcome,
        theta_pp=round(100 * theta, 3),
        ci_low_pp=round(100 * ci[0], 3),
        ci_high_pp=round(100 * ci[1], 3),
        p_value=round(p_value, 4),
        se_cluster_pp=round(100 * se, 3),
        se_naive_pp=round(100 * se_naive, 3),
        mde_pp=round(100 * mde, 2),
        n=int(dentro.sum()),
        n_contas=int(len(np.unique(grupos_validos))),
        n_tratados=tratados.height,
        eventos_tratados=int(tratados[outcome].sum()),
        overlap_min=round(float(m_hat.min()), 4),
        overlap_max=round(float(m_hat.max()), 4),
        aparados=aparados,
        significativo=significativo,
        leitura=leitura,
    )
