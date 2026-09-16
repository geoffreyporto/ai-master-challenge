"""Triagem univariada, replicação do desenho da referência e comparação de idades.

Responde três perguntas com número:
1. cada feature candidata separa quem sai de quem fica? (AUC + Holm)
2. o desenho da referência reproduz aqui? (ROC-AUC e precisão média)
3. idade da conta e idade da assinatura são o mesmo sinal?
"""

from __future__ import annotations

import json

import numpy as np
import polars as pl
from scipy import stats
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import average_precision_score, roc_auc_score

from churn_diag.account_panel import (
    ACCOUNT_CATEGORICAL,
    ACCOUNT_NUMERIC,
    split_train_test,
)
from churn_diag.config import REFERENCE_SCREEN_JSON, SEED
from churn_diag.hypotheses import holm

AGE_CORRELATION_SAME_SIGNAL = 0.7  # Spearman a partir do qual tratamos como o mesmo
AGE_MODEL_GAIN_TOLERANCE = 0.02  # ganho de ROC que consideramos relevante


def univariate_screening(
    panel: pl.DataFrame, features: list[str], label: str = "y"
) -> pl.DataFrame:
    """AUC, p (Mann-Whitney) e p ajustado por Holm para cada feature."""
    rows = []
    for f in features:
        d = panel.select(f, label).drop_nulls()
        y = d[label].to_numpy()
        x = d[f].cast(pl.Float64).to_numpy()
        if len(np.unique(y)) < 2 or len(np.unique(x)) < 2:
            rows.append(
                {
                    "feature": f,
                    "n": d.height,
                    "n_pos": int(y.sum()),
                    "auc": float("nan"),
                    "p_value": 1.0,
                }
            )
            continue
        auc = float(roc_auc_score(y, x))
        p = float(stats.mannwhitneyu(x[y == 1], x[y == 0]).pvalue)
        rows.append(
            {
                "feature": f,
                "n": d.height,
                "n_pos": int(y.sum()),
                "auc": round(auc, 4),
                "p_value": p,
            }
        )
    out = pl.DataFrame(rows)
    return (
        out.with_columns(
            p_holm=pl.Series(holm(out["p_value"].to_list())),
            direction=pl.when(pl.col("auc") >= 0.5)
            .then(pl.lit("maior = mais risco"))
            .otherwise(pl.lit("menor = mais risco")),
        )
        .with_columns(
            abs_lift=(pl.col("auc") - 0.5).abs().round(4),
            significant=pl.col("p_holm") < 0.05,
            p_value=pl.col("p_value").round(6),
            p_holm=pl.col("p_holm").round(6),
        )
        .sort("abs_lift", descending=True)
    )


def _matrix(
    df: pl.DataFrame,
    numeric: list[str],
    categorical: list[str],
    categories: dict[str, list[str]] | None = None,
) -> tuple[np.ndarray, dict[str, list[str]]]:
    if categories is None:
        categories = {c: sorted(df[c].unique().to_list()) for c in categorical}
    medians = {c: df[c].cast(pl.Float64).median() for c in numeric}
    cols = [
        pl.col(c)
        .cast(pl.Float64)
        .fill_null(medians[c] if medians[c] is not None else 0.0)
        for c in numeric
    ]
    cols += [
        (pl.col(c) == v).cast(pl.Float64).alias(f"{c}={v}")
        for c, values in categories.items()
        for v in values
    ]
    return df.select(cols).to_numpy(), categories


def _gbm() -> HistGradientBoostingClassifier:
    """Mesmos hiperparâmetros do script da referência."""
    return HistGradientBoostingClassifier(
        max_depth=3,
        learning_rate=0.05,
        max_iter=120,
        l2_regularization=2.0,
        random_state=SEED,
    )


def _fit_score(
    train: pl.DataFrame, test: pl.DataFrame, numeric: list[str], categorical: list[str]
) -> tuple[float, float]:
    x_tr, cats = _matrix(train, numeric, categorical)
    x_te, _ = _matrix(test, numeric, categorical, cats)
    model = _gbm().fit(x_tr, train["y"].to_numpy())
    p = model.predict_proba(x_te)[:, 1]
    y = test["y"].to_numpy()
    return float(roc_auc_score(y, p)), float(average_precision_score(y, p))


def reference_replication(panel: pl.DataFrame) -> dict[str, float]:
    """Replica a triagem da referência e devolve as métricas do recorte de teste."""
    train, test = split_train_test(panel)
    roc, ap = _fit_score(train, test, list(ACCOUNT_NUMERIC), list(ACCOUNT_CATEGORICAL))
    return {
        "train_rows": train.height,
        "test_rows": test.height,
        "train_positive_rate": round(float(train["y"].mean()), 4),
        "test_positive_rate": round(float(test["y"].mean()), 4),
        "test_roc_auc": round(roc, 4),
        "test_average_precision": round(ap, 4),
    }


def age_signal_comparison(panel: pl.DataFrame) -> pl.DataFrame:
    """Idade da conta × idade da assinatura mais nova: AUC, correlação e modelos."""
    train, test = split_train_test(panel)
    d = panel.select("tenure_days", "min_sub_age_days").drop_nulls()
    rho = float(
        stats.spearmanr(
            d["tenure_days"].to_numpy(), d["min_sub_age_days"].to_numpy()
        ).statistic
    )
    uni = univariate_screening(test, ["tenure_days", "min_sub_age_days"])
    auc = dict(zip(uni["feature"], uni["auc"], strict=True))
    models = {
        "só idade da conta": ["tenure_days"],
        "só idade da assinatura": ["min_sub_age_days"],
        "as duas": ["tenure_days", "min_sub_age_days"],
    }
    rows = []
    for name, feats in models.items():
        roc, ap = _fit_score(train, test, feats, [])
        rows.append(
            {
                "modelo": name,
                "roc_auc": round(roc, 4),
                "average_precision": round(ap, 4),
            }
        )
    out = pl.DataFrame(rows)
    best_single = max(out["roc_auc"][0], out["roc_auc"][1])
    gain = out["roc_auc"][2] - best_single
    same = rho >= AGE_CORRELATION_SAME_SIGNAL and gain <= AGE_MODEL_GAIN_TOLERANCE
    verdict = (
        "mesmo sinal: as duas idades andam juntas e juntá-las não melhora o modelo"
        if same
        else "sinais distintos: as idades não andam juntas ou juntá-las melhora o modelo"
    )
    return out.with_columns(
        spearman_tenure_vs_sub_age=round(rho, 3),
        auc_tenure_days=auc.get("tenure_days"),
        auc_min_sub_age_days=auc.get("min_sub_age_days"),
        ganho_ao_juntar=round(float(gain), 4),
        veredito=pl.lit(verdict),
    )


def published_reference_metrics(path=REFERENCE_SCREEN_JSON) -> dict[str, float]:
    """Métricas que a triagem da referência publicou (para comparar lado a lado)."""
    data = json.loads(path.read_text(encoding="utf-8"))["metrics"]
    return {
        "train_rows": int(data["train_rows"]),
        "test_rows": int(data["test_rows"]),
        "test_roc_auc": float(data["test_roc_auc"]),
        "test_average_precision": float(data["test_average_precision"]),
    }
