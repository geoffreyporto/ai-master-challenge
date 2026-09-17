"""Exporta o modelo B0 + política para o roteador Rust, e o golden do hold-out."""

from __future__ import annotations

import gzip
import json
from collections.abc import Sequence
from pathlib import Path

import numpy as np

from support_redesign.boundary import Decision, Policy
from support_redesign.classifier import TfidfLR


def export_router_model(clf: TfidfLR, policy: Policy, path: Path) -> None:
    vocab = clf.vectorizer.vocabulary_
    terms = sorted(vocab, key=vocab.__getitem__)
    payload = {
        "format": "tfidf-lr-v1",
        "classes": list(clf.classes_),
        "terms": terms,
        "idf": clf.vectorizer.idf_.tolist(),
        "coef": clf.model.coef_.tolist(),
        "intercept": clf.model.intercept_.tolist(),
        "policy": policy.to_json(),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload))


def export_dist_model(model_json: Path, dist_file: Path) -> None:
    """Cópia gzip determinística (mtime=0) distribuída junto dos binários."""
    dist_file.parent.mkdir(parents=True, exist_ok=True)
    with (
        dist_file.open("wb") as raw,
        gzip.GzipFile(
            filename="", mode="wb", fileobj=raw, mtime=0, compresslevel=9
        ) as gz,
    ):
        gz.write(model_json.read_bytes())


def export_golden(
    texts: Sequence[str], proba: np.ndarray, decisions: Sequence[Decision], path: Path
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as fh:
        for text, row, d in zip(texts, proba, decisions, strict=True):
            fh.write(
                json.dumps(
                    {
                        "text": text,
                        "proba": row.tolist(),
                        "topic": d.topic,
                        "action": d.action,
                    }
                )
                + "\n"
            )
