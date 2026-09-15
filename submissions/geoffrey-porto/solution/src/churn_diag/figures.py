"""Gráficos do relatório (PNG estático, determinístico).

Regras (skill de dataviz): um eixo por gráfico (nunca eixo duplo — duas
medidas viram dois painéis ou um índice comum), cores categóricas em ordem
fixa, texto em tinta neutra, grade recessiva, rótulos diretos seletivos.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import polars as pl  # noqa: E402

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
GRID = "#e4e3df"
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
MUTED = "#a9a8a2"
MONTHS_PT = (
    "jan",
    "fev",
    "mar",
    "abr",
    "mai",
    "jun",
    "jul",
    "ago",
    "set",
    "out",
    "nov",
    "dez",
)
SCORER_LABELS = {
    "idade_da_assinatura": "Idade da assinatura",
    "perda_esperada_mrr": "Perda esperada (idade × MRR)",
    "so_mrr": "Só MRR (maiores primeiro)",
    "logistica_todas_tabelas": "Logística (5 tabelas)",
    "gbm_todas_tabelas": "GBM (5 tabelas)",
}


def _months(dates) -> list[str]:
    return [MONTHS_PT[d.month - 1] for d in dates]


def _br(x: float, nd: int = 1) -> str:
    """Número no formato pt-BR (vírgula decimal)."""
    return f"{x:.{nd}f}".replace(".", ",")


def _style(ax: plt.Axes, title: str, subtitle: str | None = None) -> None:
    ax.set_facecolor(SURFACE)
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color(GRID)
    ax.tick_params(colors=INK_2, labelsize=9)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.set_title(title, loc="left", fontsize=11, color=INK, fontweight="bold", pad=18)
    if subtitle:
        ax.text(0, 1.02, subtitle, transform=ax.transAxes, fontsize=8.5, color=INK_2)


def _save(fig: plt.Figure, path: Path) -> Path:
    fig.patch.set_facecolor(SURFACE)
    fig.tight_layout()
    fig.savefig(path, dpi=150, metadata={"Software": None})
    plt.close(fig)
    return path


def churn_count_vs_rate(monthly: pl.DataFrame, ucl: float, path: Path) -> Path:
    m = monthly.filter(pl.col("month") >= pl.date(2024, 1, 1))
    labels = _months(m["month"])
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 3.8))
    colors = [ORANGE if p == "target" else BLUE for p in m["period"]]
    a1.bar(labels, m["ended_all"], color=colors, width=0.6)
    _style(
        a1,
        "Contagem: assinaturas encerradas por mês (2024)",
        "laranja = 4º tri · a contagem cresce junto com a base",
    )
    a2.plot(
        labels,
        100 * m["mrr_churn_rate"],
        color=BLUE,
        linewidth=2,
        marker="o",
        markersize=5,
    )
    a2.axhline(100 * ucl, color=MUTED, linewidth=1, linestyle="--")
    a2.text(
        0,
        100 * ucl + 0.03,
        " limite de controle (média jan–set + 3σ)",
        fontsize=8,
        color=INK_2,
        va="bottom",
    )
    for x, y in zip(
        labels[-3:], (100 * m["mrr_churn_rate"]).to_list()[-3:], strict=True
    ):
        a2.annotate(
            f"{_br(y)}%",
            (x, y),
            textcoords="offset points",
            xytext=(0, 7),
            ha="center",
            fontsize=8.5,
            color=INK,
        )
    a2.set_ylabel("% do MRR ativo no 1º dia", color=INK_2, fontsize=9)
    _style(
        a2,
        "Taxa: churn de MRR por mês (2024)",
        "estável ~0,8%/mês até set; rompe o limite em out–dez",
    )
    return _save(fig, path)


def hazard_by_age(hz: pl.DataFrame, order: list[str], path: Path) -> Path:
    fig, ax = plt.subplots(figsize=(8.5, 3.8))
    width = 0.38
    xs = range(len(order))
    for i, (period, color, name) in enumerate(
        (("reference", BLUE, "jan–set/2024"), ("target", ORANGE, "out–dez/2024"))
    ):
        d = {
            r["age_bucket"]: r["hazard"]
            for r in hz.filter(pl.col("period") == period).iter_rows(named=True)
        }
        vals = [100 * d.get(b, 0.0) for b in order]
        pos = [x + (i - 0.5) * width for x in xs]
        ax.bar(pos, vals, width=width - 0.03, color=color, label=name)
        for x, v in zip(pos, vals, strict=True):
            ax.text(x, v + 0.1, _br(v), ha="center", fontsize=8, color=INK_2)
    ax.set_xticks(list(xs), order)
    ax.set_xlabel("idade da assinatura", color=INK_2, fontsize=9)
    ax.set_ylabel("% que sai no mês", color=INK_2, fontsize=9)
    ax.legend(frameon=False, fontsize=9, labelcolor=INK_2)
    _style(
        ax,
        "Risco mensal de saída por idade da assinatura",
        "a piora está nas assinaturas novas; as maduras quase não mudaram",
    )
    return _save(fig, path)


def usage_vs_base(usage_idx: pl.DataFrame, path: Path) -> Path:
    fig, ax = plt.subplots(figsize=(8.5, 3.6))
    labels = _months(usage_idx["month"])
    for col, color, name in (
        ("active_idx", ORANGE, "assinaturas ativas"),
        ("usage_idx", BLUE, "uso total da plataforma"),
    ):
        vals = usage_idx[col].to_list()
        ax.plot(labels, vals, color=color, linewidth=2)
        ax.text(
            len(labels) - 1 + 0.15,
            vals[-1],
            f"{name}\n{vals[-1]:.0f}",
            fontsize=8.5,
            color=INK,
            va="center",
        )
    ax.axhline(100, color=MUTED, linewidth=1, linestyle=":")
    ax.set_xlim(-0.3, len(labels) + 1.6)
    ax.set_ylabel("índice (jan/2024 = 100)", color=INK_2, fontsize=9)
    _style(
        ax,
        "“O uso cresceu”? A base cresceu; o uso ficou parado",
        "índice jan/2024 = 100 — mesma escala para as duas séries",
    )
    return _save(fig, path)


def data_quality(items: list[tuple[str, float]], path: Path) -> Path:
    fig, ax = plt.subplots(figsize=(8.5, 3.4))
    names = [n for n, _ in items][::-1]
    vals = [v for _, v in items][::-1]
    ax.barh(names, vals, color=BLUE, height=0.55)
    for y, v in enumerate(vals):
        ax.text(v + 1, y, f"{_br(v, 0)}%", va="center", fontsize=9, color=INK)
    ax.set_xlim(0, 100)
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    ax.grid(axis="y", visible=False)
    _style(
        ax,
        "Quanto dos dados contradiz o ciclo de vida do cliente",
        "% dos registros de cada fonte",
    )
    return _save(fig, path)


def oot_models(oot: pl.DataFrame, path: Path) -> Path:
    fig, ax = plt.subplots(figsize=(8.5, 3.6))
    names = [SCORER_LABELS.get(n, n) for n in oot["scorer"]]
    ys = range(len(names))
    h = 0.36
    ax.barh(
        [y + h / 2 for y in ys],
        oot["roc_auc_in_sample"],
        height=h - 0.03,
        color=MUTED,
        label="no treino (jul/24)",
    )
    ax.barh(
        [y - h / 2 for y in ys],
        oot["roc_auc"],
        height=h - 0.03,
        color=BLUE,
        label="fora do tempo (out/24)",
    )
    for y, v in zip(ys, oot["roc_auc"], strict=True):
        ax.text(v + 0.01, y - h / 2, _br(v, 2), va="center", fontsize=8.5, color=INK)
    ax.axvline(0.5, color=ORANGE, linewidth=1.2, linestyle="--")
    ax.text(0.505, -0.75, "acaso (0,5)", color=INK_2, fontsize=8.5)
    ax.set_yticks(list(ys), names)
    ax.set_xlim(0.4, 1.05)
    ax.set_xlabel("ROC-AUC", color=INK_2, fontsize=9)
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    ax.grid(axis="y", visible=False)
    ax.legend(frameon=False, fontsize=8.5, loc="lower right", labelcolor=INK_2)
    _style(
        ax,
        "Mais variáveis não ajudam: o GBM decora o treino e empata com o acaso",
        "só a idade da assinatura mantém sinal fora do tempo",
    )
    return _save(fig, path)
