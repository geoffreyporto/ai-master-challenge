"""Fronteira IA × humano: limiares por fila, conformal e política (fronteira-automacao)."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from typing import Any, Literal

import numpy as np

from support_redesign.config import (
    CONFIRM_PRIORITIES,
    CONFORMAL_ALPHA,
    HUMAN_ONLY_TOPICS,
    N_HUMAN_EXAMPLES,
    OOD_QUANTILE,
    SEED,
    TARGET_PRECISION,
)

Action = Literal["auto", "confirmar", "humano"]
MIN_SUPPORT = 20


@dataclass(frozen=True)
class Policy:
    classes: tuple[str, ...]
    thresholds: dict[str, float | None]
    qhat: float
    min_known_share: float
    target_precision: float = TARGET_PRECISION
    alpha: float = CONFORMAL_ALPHA
    human_only: tuple[str, ...] = tuple(sorted(HUMAN_ONLY_TOPICS))
    confirm_priorities: tuple[str, ...] = tuple(sorted(CONFIRM_PRIORITIES))

    def to_json(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Decision:
    topic: str
    confidence: float
    margin: float
    prediction_set: tuple[str, ...]
    action: Action
    reason: str
    rule: str


def class_thresholds(
    proba: np.ndarray, y_idx: np.ndarray, classes: Sequence[str], target: float
) -> dict[str, float | None]:
    """Menor limiar com precisão ≥ meta entre os previstos daquela fila (validação)."""
    pred = proba.argmax(axis=1)
    conf = proba.max(axis=1)
    out: dict[str, float | None] = {}
    for c, name in enumerate(classes):
        mask = pred == c
        order = np.argsort(-conf[mask])
        c_conf = conf[mask][order]
        hits = (y_idx[mask][order] == c).astype(float)
        precision = np.cumsum(hits) / np.arange(1, len(hits) + 1)
        ok = np.flatnonzero(
            (precision >= target) & (np.arange(1, len(hits) + 1) >= MIN_SUPPORT)
        )
        out[name] = float(c_conf[ok.max()]) if ok.size else None
    return out


def conformal_qhat(proba: np.ndarray, y_idx: np.ndarray, alpha: float) -> float:
    scores = 1.0 - proba[np.arange(len(y_idx)), y_idx]
    n = len(scores)
    level = min(math.ceil((n + 1) * (1 - alpha)) / n, 1.0)
    return float(np.quantile(scores, level, method="higher"))


def fit_policy(
    proba_val: np.ndarray,
    y_val_idx: np.ndarray,
    classes: Sequence[str],
    known_val: np.ndarray,
) -> Policy:
    return Policy(
        classes=tuple(classes),
        thresholds=class_thresholds(proba_val, y_val_idx, classes, TARGET_PRECISION),
        qhat=conformal_qhat(proba_val, y_val_idx, CONFORMAL_ALPHA),
        min_known_share=float(np.quantile(known_val, OOD_QUANTILE)),
    )


def decide(
    policy: Policy,
    row: np.ndarray,
    priority: str | None = None,
    known_share: float = 1.0,
) -> Decision:
    order = np.argsort(-row)
    top = policy.classes[order[0]]
    conf = float(row[order[0]])
    margin = conf - float(row[order[1]])
    pset = tuple(policy.classes[i] for i in np.flatnonzero(row >= 1.0 - policy.qhat))
    thr = policy.thresholds.get(top)

    def make(action: Action, rule: str, reason: str) -> Decision:
        return Decision(top, conf, margin, pset, action, reason, rule)

    if known_share < policy.min_known_share:
        return make(
            "humano", "ood", f"fora do domínio: {known_share:.0%} dos termos conhecidos"
        )
    if len(pset) != 1:
        return make("humano", "conformal", f"conjunto conformal com {len(pset)} filas")
    if top in policy.human_only:
        return make("humano", "human_only", f"fila {top} é só-humano")
    if thr is None:
        return make(
            "humano",
            "no_threshold",
            f"fila {top} não atinge a precisão-alvo na validação",
        )
    if conf < thr:
        return make(
            "humano",
            "low_confidence",
            f"confiança {conf:.3f} abaixo do limiar {thr:.3f}",
        )
    if priority in policy.confirm_priorities:
        return make(
            "confirmar", "confirm", f"prioridade {priority} exige confirmação humana"
        )
    return make("auto", "auto", f"confiança {conf:.3f} ≥ limiar {thr:.3f}")


def decide_all(
    policy: Policy,
    proba: np.ndarray,
    priorities: Sequence[str | None] | None = None,
    known: Sequence[float] | None = None,
) -> list[Decision]:
    prios = priorities if priorities is not None else [None] * len(proba)
    shares = known if known is not None else [1.0] * len(proba)
    return [
        decide(policy, r, p, float(k))
        for r, p, k in zip(proba, prios, shares, strict=True)
    ]


def policy_report(
    policy: Policy, proba: np.ndarray, y_idx: np.ndarray, decisions: Sequence[Decision]
) -> dict[str, Any]:
    actions = np.array([d.action for d in decisions])
    pred = proba.argmax(axis=1)
    auto = actions == "auto"
    in_set = [
        policy.classes[y] in d.prediction_set
        for y, d in zip(y_idx, decisions, strict=True)
    ]
    per_class = {}
    for c, name in enumerate(policy.classes):
        m = pred == c
        a = m & auto
        per_class[name] = {
            "threshold": policy.thresholds[name],
            "predicted": int(m.sum()),
            "auto": int(a.sum()),
            "auto_share": float(a.sum() / max(m.sum(), 1)),
            "auto_precision": float((y_idx[a] == c).mean()) if a.any() else None,
        }
    return {
        "n": len(decisions),
        "coverage_auto": float(auto.mean()),
        "precision_auto": float((pred[auto] == y_idx[auto]).mean())
        if auto.any()
        else None,
        "human_share": float((actions == "humano").mean()),
        "confirm_share": float((actions == "confirmar").mean()),
        "accuracy_all": float((pred == y_idx).mean()),
        "conformal_coverage": float(np.mean(in_set)),
        "mean_set_size": float(np.mean([len(d.prediction_set) for d in decisions])),
        "per_class": per_class,
    }


def risk_coverage(
    proba: np.ndarray, y_idx: np.ndarray, points: int = 50
) -> list[dict[str, float]]:
    conf = proba.max(axis=1)
    correct = proba.argmax(axis=1) == y_idx
    out = []
    for t in np.linspace(0.0, float(conf.max()), points, endpoint=False):
        m = conf >= t
        out.append(
            {
                "threshold": float(t),
                "coverage": float(m.mean()),
                "precision": float(correct[m].mean()),
            }
        )
    return out


def human_examples(
    texts: Sequence[str],
    labels: Sequence[str],
    decisions: Sequence[Decision],
    n: int = N_HUMAN_EXAMPLES,
    seed: int = SEED,
) -> list[dict[str, Any]]:
    idx = [i for i, d in enumerate(decisions) if d.action == "humano"]
    rng = np.random.default_rng(seed)
    chosen = sorted(rng.choice(idx, size=min(n, len(idx)), replace=False).tolist())
    return [
        {
            "texto": texts[i][:220],
            "fila_verdadeira": labels[i],
            "fila_prevista": decisions[i].topic,
            "confianca": round(decisions[i].confidence, 3),
            "motivo": decisions[i].reason,
        }
        for i in chosen
    ]


SECOND_OPINION_RULES = frozenset({"conformal", "low_confidence"})


def second_opinion_eligible(decisions: Sequence[Decision]) -> list[int]:
    """Tickets que só foram para humano por incerteza (não por regra de risco)."""
    return [i for i, d in enumerate(decisions) if d.rule in SECOND_OPINION_RULES]


def second_opinion(
    decisions: Sequence[Decision],
    y_idx: np.ndarray,
    classes: Sequence[str],
    hosted_labels: dict[int, str | None],
    target: float = TARGET_PRECISION,
) -> dict[str, Any]:
    """Concordância local × hospedado entre os elegíveis: precisão e cobertura extra."""
    eligible = second_opinion_eligible(decisions)
    agree = [i for i in eligible if hosted_labels.get(i) == decisions[i].topic]
    hits = [classes[y_idx[i]] == decisions[i].topic for i in agree]
    precision = float(np.mean(hits)) if hits else None
    return {
        "eligible": len(eligible),
        "agree": len(agree),
        "precision": precision,
        "extra_coverage": len(agree) / max(len(decisions), 1),
        "enabled": precision is not None
        and len(agree) >= MIN_SUPPORT
        and precision >= target,
    }
