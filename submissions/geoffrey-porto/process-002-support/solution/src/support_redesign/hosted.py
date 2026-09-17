"""Classificação hospedada: GLiNER2 com fallback e LLM como classificador (AC-030, AC-031)."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import numpy as np
import polars as pl
from sklearn.metrics import accuracy_score, f1_score

from support_redesign.config import (
    LLM_SAMPLE_PER_CLASS,
    PIONEER_CLASSIFIER,
    PIONEER_CLASSIFIER_FALLBACK,
    PIONEER_LLM,
    SEED,
    TOPICS,
)
from support_redesign.pioneer import PioneerClient, PioneerUnavailableError

LABELS = {t.lower(): t for t in TOPICS}
SCHEMA = {"classifications": [{"task": "topic_group", "labels": list(LABELS)}]}
LLM_PROMPT = (
    "You route IT support tickets. The ticket text is lowercased and has stopwords "
    "removed. Answer with exactly one queue name from this list and nothing else: "
    + ", ".join(LABELS)
    + ".\n\nTicket: {text}"
)


def classify(client: PioneerClient, text: str) -> dict[str, Any]:
    """Modelo principal; se ele falhar ou se abstiver (`null`), o fallback atende."""
    for model, fallback in (
        (PIONEER_CLASSIFIER, False),
        (PIONEER_CLASSIFIER_FALLBACK, True),
    ):
        try:
            out = client.infer(model, text, SCHEMA)
        except PioneerUnavailableError:
            continue
        head = out["result"].get("topic_group") or {}
        if not head.get("label") and not fallback:
            continue  # o modelo principal se absteve: o fallback responde
        return {
            "label": LABELS.get(str(head.get("label", "")).lower()),
            "confidence": float(head.get("confidence", 0.0)),
            "model_used": out.get("model_used", model),
            "fallback": fallback,
            "latency_ms": float(out.get("latency_ms", 0.0)),
            "client_ms": float(out.get("client_ms", 0.0)),
            "tokens": int(out.get("token_usage", 0)),
        }
    return {
        "label": None,
        "confidence": 0.0,
        "model_used": None,
        "fallback": True,
        "latency_ms": 0.0,
        "client_ms": 0.0,
        "tokens": 0,
    }


def parse_llm_label(content: str) -> str | None:
    low = content.lower()
    for name in sorted(LABELS, key=len, reverse=True):
        if name in low:
            return LABELS[name]
    return None


def classify_llm(client: PioneerClient, text: str) -> dict[str, Any]:
    out = client.chat(
        PIONEER_LLM, [{"role": "user", "content": LLM_PROMPT.format(text=text)}]
    )
    return {
        "label": parse_llm_label(out["content"]),
        "raw": out["content"][:80],
        "confidence": 1.0,
        "model_used": PIONEER_LLM,
        "client_ms": out["client_ms"],
        "tokens": out["tokens"],
    }


def stratified_sample(
    test: pl.DataFrame, per_class: int = LLM_SAMPLE_PER_CLASS, seed: int = SEED
) -> pl.DataFrame:
    return (
        test.with_columns(
            pl.int_range(pl.len()).shuffle(seed=seed).over("Topic_group").alias("_r")
        )
        .filter(pl.col("_r") < per_class)
        .drop("_r")
        .sort("row_id")
    )


def evaluate_top1(
    name: str, results: Sequence[dict[str, Any]], labels: Sequence[str]
) -> dict[str, Any]:
    pred = [r["label"] or "Miscellaneous" for r in results]
    conf = np.array([r["confidence"] for r in results])
    correct = np.array([p == y for p, y in zip(pred, labels, strict=True)])
    edges = np.linspace(0, 1, 16)
    ece = sum(
        m.mean() * abs(correct[m].mean() - conf[m].mean())
        for lo, hi in zip(edges[:-1], edges[1:], strict=True)
        if (m := (conf > lo) & (conf <= hi)).any()
    )
    served: dict[str, int] = {}
    for r in results:
        served[str(r.get("model_used"))] = served.get(str(r.get("model_used")), 0) + 1
    per_class = f1_score(labels, pred, average=None, labels=list(TOPICS))
    return {
        "model": name,
        "n": len(labels),
        "accuracy": float(accuracy_score(labels, pred)),
        "macro_f1": float(f1_score(labels, pred, average="macro")),
        "f1_per_class": dict(zip(TOPICS, map(float, per_class), strict=True)),
        "ece": float(ece),
        "median_client_ms": float(
            np.median([r.get("client_ms", 0.0) for r in results])
        ),
        "unparsed": sum(r["label"] is None for r in results),
        "fallback_used": sum(bool(r.get("fallback")) for r in results),
        "served_by": served,
        "tokens_total": int(sum(r.get("tokens", 0) for r in results)),
    }
