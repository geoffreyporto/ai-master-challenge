"""Diagnóstico operacional do Dataset 1 (feature diagnostico-operacional)."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal

import numpy as np
import polars as pl
from scipy import stats
from statsmodels.miscmodels.ordinal_model import OrderedModel
from statsmodels.stats.power import TTestIndPower

DIMENSIONS = ("Ticket Channel", "Ticket Priority", "Ticket Type")
CSAT = "Customer Satisfaction Rating"
ALPHA = 0.05
POWER = 0.80

Base = Literal["sintetico", "real"]
Tipo = Literal["descricao", "predicao", "cenario"]


@dataclass(frozen=True)
class Finding:
    id: str
    texto: str
    base: Base
    tipo: Tipo


def closed_with_hours(d1: pl.DataFrame) -> pl.DataFrame:
    delta = pl.col("Time to Resolution") - pl.col("First Response Time")
    return d1.filter(pl.col("Ticket Status") == "Closed").with_columns(
        (delta.dt.total_seconds() / 3600).alias("hours")
    )


def segments(closed: pl.DataFrame) -> pl.DataFrame:
    return (
        closed.group_by(*DIMENSIONS)
        .agg(
            pl.len().alias("n"),
            pl.col("hours").median().alias("median_hours"),
            pl.col(CSAT).mean().alias("csat_mean"),
        )
        .sort("median_hours", descending=True)
    )


def kruskal(closed: pl.DataFrame, dim: str, metric: str) -> dict[str, float]:
    groups = [g[metric].drop_nulls().to_numpy() for _, g in closed.group_by(dim)]
    h, p = stats.kruskal(*groups)
    n = sum(len(g) for g in groups)
    k = len(groups)
    return {
        "H": float(h),
        "p": float(p),
        "epsilon2": float(max(h - k + 1, 0) / (n - k)),
    }


def csat_mde_between_channels(closed: pl.DataFrame) -> dict[str, float]:
    n_min = int(closed.group_by("Ticket Channel").len()["len"].min() or 0)
    sd = float(closed[CSAT].std() or 0.0)
    d = TTestIndPower().solve_power(nobs1=n_min, alpha=ALPHA, power=POWER, ratio=1.0)
    means = closed.group_by("Ticket Channel").agg(pl.col(CSAT).mean())[CSAT]
    return {
        "n_min_per_channel": n_min,
        "csat_sd": sd,
        "cohen_d": float(d),
        "mde_points": float(d * sd),
        "observed_max_diff": float(means.max() - means.min()),
    }


def ordinal_csat(closed: pl.DataFrame) -> dict[str, float]:
    data = closed.drop_nulls([CSAT, "hours", "Customer Age"])
    dummies = data.select(DIMENSIONS).to_dummies(drop_first=True)
    x = np.column_stack(
        [dummies.to_numpy().astype(float), data["Customer Age"], data["hours"]]
    )
    y = data[CSAT].to_numpy().astype(int)
    fit = OrderedModel(y, x, distr="logit").fit(method="bfgs", disp=False, maxiter=500)
    _, counts = np.unique(y, return_counts=True)
    ll_null = float(np.sum(counts * np.log(counts / counts.sum())))
    ll = float(fit.llf)
    lr = 2 * (ll - ll_null)
    df = x.shape[1]
    return {
        "n": int(len(y)),
        "features": int(df),
        "pseudo_r2": 1 - ll / ll_null,
        "lr_stat": lr,
        "lr_p": float(stats.chi2.sf(lr, df)),
    }


def status_mix(d1: pl.DataFrame) -> dict[str, float]:
    mix = d1["Ticket Status"].value_counts(normalize=True)
    return dict(
        zip(mix["Ticket Status"].to_list(), mix["proportion"].to_list(), strict=True)
    )


def waste_from_file(closed: pl.DataFrame) -> dict[str, Any]:
    negative = float((closed["hours"] < 0).mean() or 0.0)
    return {
        "hours": None,
        "lacuna": True,
        "motivo": (
            f"{negative:.1%} dos tickets fechados têm resolução antes da primeira "
            "resposta; o arquivo não mede duração. O desperdício vem do cenário de ROI."
        ),
        "negative_interval_share": negative,
    }


def diagnose(d1: pl.DataFrame) -> dict[str, Any]:
    closed = closed_with_hours(d1)
    seg = segments(closed)
    tests = {
        f"{metric}|{dim}": kruskal(closed, dim, metric)
        for dim in DIMENSIONS
        for metric in ("hours", CSAT)
    }
    all_null = all(t["p"] >= ALPHA for t in tests.values())
    mde = csat_mde_between_channels(closed)
    ordinal = ordinal_csat(closed)
    worst = seg.row(0, named=True)
    findings = [
        Finding(
            "F-01",
            f"Pior segmento por mediana de horas: {worst['Ticket Channel']} / "
            f"{worst['Ticket Priority']} / {worst['Ticket Type']} "
            f"({worst['median_hours']:.2f} h, n={worst['n']}) — não significativo.",
            "sintetico",
            "descricao",
        ),
        Finding(
            "F-02",
            "Nenhuma dimensão (canal, prioridade, tipo) muda horas ou CSAT de forma "
            "detectável."
            if all_null
            else "Há ao menos uma dimensão com diferença significativa.",
            "sintetico",
            "descricao",
        ),
        Finding(
            "F-03",
            f"O teste detectaria diferença de CSAT entre canais ≥ {mde['mde_points']:.2f} "
            f"ponto; a maior diferença observada é {mde['observed_max_diff']:.2f}.",
            "sintetico",
            "descricao",
        ),
        Finding(
            "F-04",
            f"Modelo ordinal de CSAT explica {ordinal['pseudo_r2']:.4f} (pseudo-R²).",
            "sintetico",
            "predicao",
        ),
    ]
    return {
        "segments": seg,
        "tests": tests,
        "no_detectable_driver": all_null,
        "mde": mde,
        "ordinal": ordinal,
        "status_mix": status_mix(d1),
        "waste": waste_from_file(closed),
        "findings": [asdict(f) for f in findings],
    }
