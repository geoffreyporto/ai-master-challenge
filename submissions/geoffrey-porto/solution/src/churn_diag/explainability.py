"""Explicabilidade como auditoria — valores de Shapley exatos, sem `shap`.

A biblioteca `shap` depende de `numba`, que não suporta Python 3.14. Em vez de
trocar a stack, aqui os valores de Shapley são calculados **exatos**, por
enumeração das 2^k coalizões, com a função de valor intervencional:

    v(S) = E_background[ f(x_S, X_-S) ]

ou seja, o que o modelo prevê quando as variáveis de S valem as da conta e as
demais vêm de uma amostra de referência. Com k = 8 são 256 coalizões — exato e
barato. Acima disso o custo dobra por variável.

Leitura desta entrega: o modelo com as cinco tabelas empata com o acaso fora do
tempo, então estes gráficos servem para **auditar** (mostrar que não há
estrutura estável), não para contar história sobre variáveis sem sinal.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from itertools import combinations
from math import factorial
from pathlib import Path

import numpy as np
import polars as pl

from churn_diag.figures import (
    BLUE,
    INK,
    INK_2,
    MUTED,
    ORANGE,
    SURFACE,
    _br,
    _save,
    _style,
)

AUDIT_FEATURES: tuple[str, ...] = (
    "age_days",
    "mrr_amount",
    "seats",
    "tenure_days",
    "u_count",
    "u_errors",
    "t_n",
    "t_csat",
)
MAX_EXACT_FEATURES = 12
BACKGROUND_SIZE = 40
EXPLAIN_ROWS = 150


def _coalition_value(
    predict: Callable[[np.ndarray], np.ndarray],
    x: np.ndarray,
    background: np.ndarray,
    mask: tuple[int, ...],
) -> np.ndarray:
    """v(S) para todas as linhas: variáveis de S vêm da conta, o resto do fundo."""
    n, n_bg = len(x), len(background)
    grid = np.repeat(background[None, :, :], n, axis=0)  # (n, n_bg, k)
    for j in mask:
        grid[:, :, j] = x[:, j][:, None]
    preds = predict(grid.reshape(n * n_bg, x.shape[1]))
    return preds.reshape(n, n_bg).mean(axis=1)


def exact_shapley_values(
    predict: Callable[[np.ndarray], np.ndarray],
    x: np.ndarray,
    background: np.ndarray,
) -> tuple[np.ndarray, float]:
    """Valores de Shapley exatos + valor base. Devolve (phi, base)."""
    k = x.shape[1]
    if k > MAX_EXACT_FEATURES:
        raise ValueError(
            f"cálculo exato só até {MAX_EXACT_FEATURES} variáveis (pedidas {k})"
        )
    indices = range(k)
    valores: dict[tuple[int, ...], np.ndarray] = {}
    for tamanho in range(k + 1):
        for subconjunto in combinations(indices, tamanho):
            valores[subconjunto] = _coalition_value(predict, x, background, subconjunto)

    phi = np.zeros_like(x, dtype=float)
    for j in indices:
        outras = [i for i in indices if i != j]
        for tamanho in range(k):
            peso = factorial(tamanho) * factorial(k - tamanho - 1) / factorial(k)
            for subconjunto in combinations(outras, tamanho):
                com_j = tuple(sorted((*subconjunto, j)))
                phi[:, j] += peso * (valores[com_j] - valores[subconjunto])
    return phi, float(valores[()][0])


def shapley_frame(
    phi: np.ndarray, x: np.ndarray, names: tuple[str, ...], envs: np.ndarray
) -> pl.DataFrame:
    """Contribuição média por variável, global e por ambiente (AC-041)."""
    linhas = []
    for j, nome in enumerate(names):
        linha = {
            "feature": nome,
            "mean_abs_shapley": round(float(np.abs(phi[:, j]).mean()), 6),
        }
        por_ambiente = {}
        for env in sorted(set(envs)):
            mask = envs == env
            por_ambiente[env] = float(np.abs(phi[mask, j]).mean())
            linha[f"env_{env}"] = round(por_ambiente[env], 6)
        linha["std_entre_ambientes"] = round(
            float(np.std(list(por_ambiente.values()))), 6
        )
        sinais = {env: float(np.mean(phi[envs == env, j])) for env in sorted(set(envs))}
        linha["troca_de_sinal"] = bool(max(sinais.values()) > 0 > min(sinais.values()))
        linhas.append(linha)
    return pl.DataFrame(linhas).sort("mean_abs_shapley", descending=True)


# ----------------------------------------------------------------- 5 gráficos
def _colormap(valores: np.ndarray) -> np.ndarray:
    """Interpola azul → laranja pelo valor da variável (sem dependência extra)."""
    import matplotlib.colors as mcolors

    v = np.asarray(valores, dtype=float)
    faixa = np.ptp(v)
    norm = (v - v.min()) / faixa if faixa > 0 else np.full_like(v, 0.5)
    mapa = mcolors.LinearSegmentedColormap.from_list(
        "azul_laranja", [BLUE, "#d9d9d6", ORANGE]
    )
    return mapa(norm)


def beeswarm(
    phi: np.ndarray, x: np.ndarray, names: tuple[str, ...], path: Path
) -> Path:
    """1. Beeswarm: ranking global + direção, uma bolinha por conta."""
    import matplotlib.pyplot as plt

    ordem = np.argsort(np.abs(phi).mean(axis=0))
    fig, ax = plt.subplots(figsize=(9, 0.55 * len(ordem) + 2))
    rng = np.random.default_rng(42)
    for linha, j in enumerate(ordem):
        jitter = rng.uniform(-0.16, 0.16, size=phi.shape[0])
        ax.scatter(
            phi[:, j],
            linha + jitter,
            c=_colormap(x[:, j]),
            s=12,
            alpha=0.75,
            linewidths=0,
        )
    ax.axvline(0, color=MUTED, linewidth=1)
    ax.set_yticks(range(len(ordem)), [names[j] for j in ordem])
    ax.set_xlabel(
        "contribuição para o risco previsto (valor de Shapley)", color=INK_2, fontsize=9
    )
    ax.grid(axis="y", visible=False)
    _style(
        ax,
        "Contribuição por variável e por conta",
        "azul = valor baixo · laranja = valor alto · nuvem centrada em zero = sem efeito",
    )
    return _save(fig, path)


def dependence(
    phi: np.ndarray,
    x: np.ndarray,
    names: tuple[str, ...],
    *,
    feature: str,
    interaction: str,
    path: Path,
) -> Path:
    """2. Dependência: valor da variável × contribuição, colorido por outra."""
    import matplotlib.pyplot as plt

    j, c = names.index(feature), names.index(interaction)
    fig, ax = plt.subplots(figsize=(8.5, 4))
    ax.scatter(x[:, j], phi[:, j], c=_colormap(x[:, c]), s=18, alpha=0.8, linewidths=0)
    ax.axhline(0, color=MUTED, linewidth=1, linestyle="--")
    ax.set_xlabel(feature, color=INK_2, fontsize=9)
    ax.set_ylabel("contribuição", color=INK_2, fontsize=9)
    _style(
        ax,
        f"Dependência: {feature}",
        f"cor = {interaction} · degrau vertical indicaria um limiar de risco",
    )
    return _save(fig, path)


def waterfall(
    phi_row: np.ndarray,
    x_row: np.ndarray,
    names: tuple[str, ...],
    *,
    base: float,
    path: Path,
    titulo: str = "Como o modelo chegou neste risco",
) -> Path:
    """3. Waterfall: da base até a previsão daquela conta."""
    import matplotlib.pyplot as plt

    ordem = np.argsort(np.abs(phi_row))[::-1]
    fig, ax = plt.subplots(figsize=(8.5, 0.45 * len(ordem) + 2))
    acumulado = base
    for linha, j in enumerate(ordem):
        cor = ORANGE if phi_row[j] > 0 else BLUE
        ax.barh(linha, phi_row[j], left=acumulado, color=cor, height=0.6)
        ax.text(
            acumulado + phi_row[j] / 2,
            linha,
            _br(100 * phi_row[j], 2),
            ha="center",
            va="center",
            fontsize=8,
            color=INK,
        )
        acumulado += phi_row[j]
    ax.axvline(base, color=MUTED, linewidth=1, linestyle="--")
    ax.set_yticks(
        range(len(ordem)), [f"{names[j]} = {_br(float(x_row[j]), 1)}" for j in ordem]
    )
    ax.set_xlabel("risco previsto", color=INK_2, fontsize=9)
    ax.grid(axis="y", visible=False)
    _style(ax, titulo, f"linha tracejada = risco médio da base ({_br(100 * base, 1)}%)")
    return _save(fig, path)


def environment_heatmap(frame: pl.DataFrame, path: Path) -> Path:
    """4. Heatmap por ambiente: variável cuja contribuição oscila é suspeita."""
    import matplotlib.pyplot as plt

    colunas = [c for c in frame.columns if c.startswith("env_")]
    dados = frame.head(8)
    matriz = dados.select(colunas).to_numpy()
    fig, ax = plt.subplots(figsize=(1.6 * len(colunas) + 4, 0.5 * dados.height + 2.4))
    im = ax.imshow(matriz, cmap="Blues", aspect="auto")
    ax.set_xticks(
        range(len(colunas)), [c.replace("env_", "") for c in colunas], rotation=20
    )
    ax.set_yticks(range(dados.height), dados["feature"].to_list())
    for i in range(dados.height):
        for j in range(len(colunas)):
            ax.text(
                j,
                i,
                _br(100 * matriz[i, j], 2),
                ha="center",
                va="center",
                fontsize=8,
                color=INK if matriz[i, j] < matriz.max() * 0.6 else SURFACE,
            )
    fig.colorbar(im, ax=ax, label="contribuição média (|Shapley|)")
    ax.grid(visible=False)
    _style(
        ax,
        "Contribuição por ambiente (auditoria de correlação espúria)",
        "oscilar entre ambientes = atalho que não generaliza",
    )
    return _save(fig, path)


def cate_staircase(quantis: pl.DataFrame, path: Path) -> Path:
    """5. Escada de CATE: efeito por quantil, medido fora da amostra."""
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(8.5, 4))
    x = range(quantis.height)
    valores = (100 * quantis["efeito_medio"]).to_list()
    erros = (100 * quantis["erro_padrao"]).to_list()
    ax.bar(
        x,
        valores,
        yerr=erros,
        color=BLUE,
        width=0.6,
        capsize=4,
        error_kw={"ecolor": MUTED, "linewidth": 1},
    )
    ax.axhline(0, color=ORANGE, linewidth=1.2, linestyle="--")
    ax.set_xticks(list(x), quantis["quantil"].to_list())
    ax.set_xlabel("quantil do efeito previsto (menor → maior)", color=INK_2, fontsize=9)
    ax.set_ylabel("efeito medido no teste (p.p.)", color=INK_2, fontsize=9)
    _style(
        ax,
        "Escada de CATE: há quem responda mais à ação?",
        "escada inclinada = heterogeneidade aproveitável · barras planas = nada a segmentar",
    )
    return _save(fig, path)


def score_contributions(sub_risk: pl.DataFrame, account_id: str) -> pl.DataFrame:
    """Explicação EXATA do score de produção: perda esperada por assinatura (AC-043)."""
    return (
        sub_risk.filter(pl.col("account_id") == account_id)
        .select(
            "subscription_id",
            "plan_tier",
            "age_days",
            pl.col("p_churn").alias("risco_90d"),
            pl.col("paid_mrr").alias("mrr"),
            pl.col("expected_loss").alias("contribuicao"),
        )
        .sort("contribuicao", descending=True)
    )


@dataclass(frozen=True, slots=True)
class AuditArtifacts:
    """Tudo que a auditoria de explicabilidade produz."""

    phi: np.ndarray
    x: np.ndarray
    names: tuple[str, ...]
    base: float
    envs: np.ndarray
    frame: pl.DataFrame
    audit_roc: float
    efficiency_error: float
    top_row: int


def run_audit(tables, *, n_rows: int = EXPLAIN_ROWS) -> AuditArtifacts:
    """Ajusta o modelo de auditoria e calcula os valores de Shapley exatos.

    O modelo de auditoria usa só as 8 variáveis de negócio de `AUDIT_FEATURES`
    (2^8 = 256 coalizões, cálculo exato). Seu ROC fora do tempo sai junto, para
    deixar claro que ele conta a mesma história do benchmark completo.
    """
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.metrics import roc_auc_score

    from churn_diag.config import OOT_TEST_T0, OOT_TRAIN_T0, SEED
    from churn_diag.risk import build_oot_panel

    treino = build_oot_panel(tables, OOT_TRAIN_T0)
    teste = build_oot_panel(tables, OOT_TEST_T0)
    x_tr = treino.select(AUDIT_FEATURES).to_numpy().astype(float)
    x_te = teste.select(AUDIT_FEATURES).to_numpy().astype(float)
    modelo = HistGradientBoostingClassifier(
        max_depth=3, learning_rate=0.05, max_iter=200, random_state=SEED
    ).fit(x_tr, treino["y"].to_numpy())

    def predict(a: np.ndarray) -> np.ndarray:
        return modelo.predict_proba(a)[:, 1]

    roc = float(roc_auc_score(teste["y"].to_numpy(), predict(x_te)))
    rng = np.random.default_rng(SEED)
    amostra = rng.choice(len(x_te), size=min(n_rows, len(x_te)), replace=False)
    fundo = rng.choice(len(x_tr), size=min(BACKGROUND_SIZE, len(x_tr)), replace=False)
    x_amostra = x_te[np.sort(amostra)]
    phi, base = exact_shapley_values(predict, x_amostra, x_tr[fundo])
    erro = float(np.abs(phi.sum(axis=1) + base - predict(x_amostra)).max())
    envs = teste["industry"].to_numpy()[np.sort(amostra)]
    frame = shapley_frame(phi, x_amostra, AUDIT_FEATURES, envs)
    return AuditArtifacts(
        phi=phi,
        x=x_amostra,
        names=AUDIT_FEATURES,
        base=base,
        envs=envs,
        frame=frame,
        audit_roc=round(roc, 4),
        efficiency_error=erro,
        top_row=int(np.argmax(np.abs(phi).sum(axis=1))),
    )


def tidy_shapley(art: AuditArtifacts) -> pl.DataFrame:
    """Forma longa (linha × variável) para gravar em CSV e reconstruir depois."""
    n, k = art.phi.shape
    return pl.DataFrame(
        {
            "linha": np.repeat(np.arange(n), k),
            "feature": list(art.names) * n,
            "valor": art.x.reshape(-1),
            "shapley": art.phi.reshape(-1),
            "ambiente": np.repeat(art.envs.astype(str), k),
        }
    )


def arrays_from_tidy(
    tidy: pl.DataFrame,
) -> tuple[np.ndarray, np.ndarray, tuple[str, ...], np.ndarray]:
    """Inverso de `tidy_shapley`: devolve (phi, x, names, envs)."""
    names = tuple(tidy.filter(pl.col("linha") == 0)["feature"].to_list())
    n, k = tidy["linha"].n_unique(), len(names)
    phi = tidy["shapley"].to_numpy().reshape(n, k)
    x = tidy["valor"].to_numpy().reshape(n, k)
    envs = tidy["ambiente"].to_numpy().reshape(n, k)[:, 0]
    return phi, x, names, envs
