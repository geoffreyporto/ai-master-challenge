"""Modelo exportado (`router_model.json.gz`) usado direto em Python.

Mesma conta do roteador Rust: TF-IDF sublinear com norma L2, regressão
logística multinomial e fração de n-gramas conhecidos. O app público usa este
arquivo versionado em vez de treinar no primeiro acesso.
"""

from __future__ import annotations

import gzip
import json
from collections import Counter
from collections.abc import Sequence
from pathlib import Path

import numpy as np

from support_redesign.boundary import Policy
from support_redesign.text import analyzer


class ExportedModel:
    name = "B0 TF-IDF + LR (exportado)"

    def __init__(self, payload: dict) -> None:
        self.classes_: tuple[str, ...] = tuple(payload["classes"])
        self.index = {t: i for i, t in enumerate(payload["terms"])}
        self.idf = np.asarray(payload["idf"], dtype=np.float64)
        self.coef = np.asarray(payload["coef"], dtype=np.float64)
        self.intercept = np.asarray(payload["intercept"], dtype=np.float64)
        raw = payload["policy"]
        self.policy = Policy(
            classes=tuple(raw["classes"]),
            thresholds=dict(raw["thresholds"]),
            qhat=raw["qhat"],
            min_known_share=raw["min_known_share"],
            target_precision=raw["target_precision"],
            alpha=raw["alpha"],
            human_only=tuple(raw["human_only"]),
            confirm_priorities=tuple(raw["confirm_priorities"]),
        )

    @classmethod
    def load(cls, path: Path) -> ExportedModel:
        opener = gzip.open if path.suffix == ".gz" else open
        with opener(path, "rt") as fh:
            return cls(json.load(fh))

    def _scores(self, text: str) -> tuple[np.ndarray, float]:
        grams = analyzer(text)
        counts = Counter(self.index[g] for g in grams if g in self.index)
        known = sum(counts.values()) / len(grams) if grams else 0.0
        if counts:
            idx = np.fromiter(counts.keys(), dtype=np.int64)
            tf = 1.0 + np.log(np.fromiter(counts.values(), dtype=np.float64))
            w = tf * self.idf[idx]
            w /= np.linalg.norm(w)
            logits = self.coef[:, idx] @ w + self.intercept
        else:
            logits = self.intercept.copy()
        z = np.exp(logits - logits.max())
        return z / z.sum(), known

    def predict_proba(self, texts: Sequence[str]) -> np.ndarray:
        return np.vstack([self._scores(t)[0] for t in texts])

    def known_share(self, texts: Sequence[str]) -> np.ndarray:
        return np.array([self._scores(t)[1] for t in texts])
