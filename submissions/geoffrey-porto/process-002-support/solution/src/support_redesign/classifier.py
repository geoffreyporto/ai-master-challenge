"""Classificadores de fila e métricas de avaliação (feature classificador-tickets)."""

from __future__ import annotations

import time
from collections.abc import Sequence
from typing import Any, Protocol

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score

from support_redesign.config import MODEL2VEC_NAME, SEED
from support_redesign.text import analyzer, normalize


class ProbaClassifier(Protocol):
    name: str
    classes_: tuple[str, ...]

    def predict_proba(self, texts: Sequence[str]) -> np.ndarray: ...


def _logreg() -> LogisticRegression:
    return LogisticRegression(
        C=5.0, class_weight="balanced", max_iter=3000, random_state=SEED
    )


class TfidfLR:
    """B0: TF-IDF uni+bigramas (analisador próprio) + regressão logística."""

    name = "B0 TF-IDF + LR"

    def __init__(self, max_features: int = 60_000) -> None:
        self.vectorizer = TfidfVectorizer(
            analyzer=analyzer, sublinear_tf=True, min_df=2, max_features=max_features
        )
        self.model = _logreg()
        self.classes_: tuple[str, ...] = ()

    def fit(self, texts: Sequence[str], labels: Sequence[str]) -> TfidfLR:
        self.model.fit(self.vectorizer.fit_transform(texts), labels)
        self.classes_ = tuple(self.model.classes_)
        return self

    def predict_proba(self, texts: Sequence[str]) -> np.ndarray:
        return self.model.predict_proba(self.vectorizer.transform(texts))

    def known_share(self, texts: Sequence[str]) -> np.ndarray:
        """Fração dos n-gramas do texto que existem no vocabulário (guarda de domínio)."""
        vocab = self.vectorizer.vocabulary_
        grams = [analyzer(t) for t in texts]
        return np.array(
            [sum(g in vocab for g in gs) / len(gs) if gs else 0.0 for gs in grams]
        )


class Model2VecLR:
    """B1: embeddings estáticos Model2Vec + regressão logística."""

    name = "B1 Model2Vec + LR"

    def __init__(self, model_name: str = MODEL2VEC_NAME) -> None:
        from model2vec import StaticModel

        self.encoder = StaticModel.from_pretrained(model_name)
        self.model = _logreg()
        self.classes_: tuple[str, ...] = ()

    def embed(self, texts: Sequence[str]) -> np.ndarray:
        return self.encoder.encode([normalize(t) for t in texts])

    def fit(self, texts: Sequence[str], labels: Sequence[str]) -> Model2VecLR:
        self.model.fit(self.embed(texts), labels)
        self.classes_ = tuple(self.model.classes_)
        return self

    def predict_proba(self, texts: Sequence[str]) -> np.ndarray:
        return self.model.predict_proba(self.embed(texts))


def expected_calibration_error(
    proba: np.ndarray, y_idx: np.ndarray, bins: int = 15
) -> float:
    conf = proba.max(axis=1)
    correct = proba.argmax(axis=1) == y_idx
    edges = np.linspace(0.0, 1.0, bins + 1)
    ece = 0.0
    for lo, hi in zip(edges[:-1], edges[1:], strict=True):
        mask = (conf > lo) & (conf <= hi)
        if mask.any():
            ece += mask.mean() * abs(correct[mask].mean() - conf[mask].mean())
    return float(ece)


def label_index(classes: Sequence[str], labels: Sequence[str]) -> np.ndarray:
    pos = {c: i for i, c in enumerate(classes)}
    return np.array([pos[label] for label in labels])


def evaluate(
    clf: ProbaClassifier, texts: Sequence[str], labels: Sequence[str]
) -> dict[str, Any]:
    start = time.perf_counter()
    proba = clf.predict_proba(texts)
    elapsed = time.perf_counter() - start
    pred = [clf.classes_[i] for i in proba.argmax(axis=1)]
    per_class = f1_score(labels, pred, average=None, labels=list(clf.classes_))
    return {
        "model": clf.name,
        "n": len(labels),
        "accuracy": float(accuracy_score(labels, pred)),
        "macro_f1": float(f1_score(labels, pred, average="macro")),
        "f1_per_class": dict(zip(clf.classes_, map(float, per_class), strict=True)),
        "ece": expected_calibration_error(proba, label_index(clf.classes_, labels)),
        "ms_per_ticket": 1000 * elapsed / max(len(labels), 1),
    }


def pick_production(val_scores: dict[str, float]) -> str:
    """O modelo de produção sai da validação — nunca do teste (P-002)."""
    return max(val_scores, key=lambda k: val_scores[k])
