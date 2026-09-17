"""Auditoria de autenticidade dos dois datasets (feature auditoria-dados)."""

from __future__ import annotations

from typing import Any

import numpy as np
import polars as pl
from scipy import stats

from support_redesign.text import PLACEHOLDER_RE

UNIFORM_COLUMNS = (
    "Ticket Type",
    "Ticket Status",
    "Ticket Priority",
    "Ticket Channel",
    "Product Purchased",
)
README_PROMISES = {"d1_rows": 30_000, "d1_ticket_types": 3}
ALPHA = 0.05


def _chi2_uniform_p(series: pl.Series) -> float:
    counts = series.drop_nulls().value_counts()["count"].to_numpy()
    return float(stats.chisquare(counts).pvalue)


def _closed_intervals_hours(d1: pl.DataFrame) -> pl.Series:
    closed = d1.filter(pl.col("Ticket Status") == "Closed")
    delta = pl.col("Time to Resolution") - pl.col("First Response Time")
    return closed.select((delta.dt.total_seconds() / 3600).alias("h"))["h"]


def audit_d1(d1: pl.DataFrame) -> dict[str, Any]:
    desc = d1["Ticket Description"]
    placeholders = {m for s in desc.to_list() for m in PLACEHOLDER_RE.findall(s)}
    subject_type = (
        d1.group_by("Ticket Subject", "Ticket Type")
        .len()
        .pivot(on="Ticket Type", index="Ticket Subject", values="len")
        .fill_null(0)
        .drop("Ticket Subject")
        .to_numpy()
    )
    hours = _closed_intervals_hours(d1)
    closed_resolutions = d1.filter(pl.col("Ticket Status") == "Closed")["Resolution"]
    domains = sorted(
        d1["Customer Email"].str.extract(r"@(.+)$").unique().drop_nulls().to_list()
    )
    uniform_p = {c: _chi2_uniform_p(d1[c]) for c in UNIFORM_COLUMNS}
    evidence = {
        "rows": d1.height,
        "product_placeholder_share": float(
            desc.str.contains("{product_purchased}", literal=True).mean() or 0.0
        ),
        "distinct_placeholders": len(placeholders),
        "placeholder_regex": PLACEHOLDER_RE.pattern,
        "uniform_chi2_p": uniform_p,
        "subject_x_type_chi2_p": float(stats.chi2_contingency(subject_type).pvalue),
        "closed_tickets": int(hours.len()),
        "negative_interval_share": float((hours < 0).mean() or 0.0),
        "resolution_unique_share": closed_resolutions.n_unique()
        / max(closed_resolutions.len(), 1),
        "email_domains": domains,
    }
    synthetic = (
        evidence["product_placeholder_share"] > 0.99
        and all(p >= ALPHA for p in uniform_p.values())
        and evidence["negative_interval_share"] > 0.25
        and all(d.startswith("example.") for d in domains)
    )
    return {"verdict": "sintetico" if synthetic else "real", "evidence": evidence}


def audit_d2(d2: pl.DataFrame) -> dict[str, Any]:
    doc = d2["Document"]
    shares = d2["Topic_group"].value_counts()["count"].to_numpy()
    conflicting = (
        d2.group_by("Document")
        .agg(pl.col("Topic_group").n_unique())
        .filter(pl.col("Topic_group") > 1)
        .height
    )
    words = doc.str.split(" ").list.len()
    evidence = {
        "rows": d2.height,
        "placeholders": int(doc.str.contains(PLACEHOLDER_RE.pattern).sum()),
        "duplicates": d2.height - doc.n_unique(),
        "conflicting_labels": conflicting,
        "classes": int(len(shares)),
        "imbalance_ratio": float(np.max(shares) / np.min(shares)),
        "docs_with_uppercase": int(doc.str.contains("[A-Z]").sum()),
        "docs_with_digits": int(doc.str.contains("[0-9]").sum()),
        "median_words": float(words.median() or 0.0),
        "docs_under_5_words": int((words < 5).sum()),
    }
    real = (
        evidence["placeholders"] == 0
        and evidence["duplicates"] == 0
        and evidence["conflicting_labels"] == 0
        and evidence["imbalance_ratio"] >= 5
    )
    preprocessed = (
        evidence["docs_with_uppercase"] == 0 and evidence["docs_with_digits"] == 0
    )
    verdict = (
        "real_preprocessado"
        if real and preprocessed
        else ("real" if real else "suspeito")
    )
    return {"verdict": verdict, "evidence": evidence}


def readme_divergences(d1: pl.DataFrame) -> list[dict[str, Any]]:
    measured = {"d1_rows": d1.height, "d1_ticket_types": d1["Ticket Type"].n_unique()}
    labels = {
        "d1_rows": "Linhas do Dataset 1",
        "d1_ticket_types": "Valores de Ticket Type",
    }
    return [
        {"item": labels[k], "readme": v, "medido": measured[k]}
        for k, v in README_PROMISES.items()
        if measured[k] != v
    ]
