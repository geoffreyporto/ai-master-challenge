"""Score de risco: perda esperada de MRR, lista do CS e validação fora do tempo.

Regra de ouro (P-002): nenhuma variável usa informação de depois do corte T0,
e nada que só existe depois que o cliente saiu entra no score.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Protocol, Self

import numpy as np
import polars as pl
from scipy import stats
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score

from churn_diag.config import (
    OOT_HORIZON_DAYS,
    OOT_TEST_T0,
    OOT_TRAIN_T0,
    RISK_HORIZON_MONTHS,
    SEED,
    SNAPSHOT_DATE,
    TOP_FRACTION,
    YOUNG_AGE_DAYS,
)
from churn_diag.loader import Tables
from churn_diag.metrics import age_bucket_expr, hazard_table

NUMERIC_FEATURES: tuple[str, ...] = (
    "age_days",
    "seats",
    "mrr_amount",
    "u_count",
    "u_errors",
    "u_breadth",
    "u_beta_share",
    "t_n",
    "t_esc",
    "t_csat",
    "t_csat_missing",
    "t_frt",
    "t_res",
    "prior_churn_events",
    "acct_seats",
    "tenure_days",
)
BOOL_FEATURES: tuple[str, ...] = ("upgrade_flag", "downgrade_flag", "auto_renew_flag")
CAT_FEATURES: tuple[str, ...] = (
    "plan_tier",
    "billing_frequency",
    "industry",
    "country",
    "referral_source",
)


# ------------------------------------------------------------- painel OOT (T0)
def build_oot_panel(
    t: Tables, t0: date, horizon_days: int = OOT_HORIZON_DAYS
) -> pl.DataFrame:
    """Assinaturas pagas ativas em T0; variáveis só com dados < T0; y em [T0, T0+H)."""
    t1 = t0 + timedelta(days=horizon_days)
    subs = t.subscriptions.filter(
        pl.col("start_date") < t0,
        pl.col("end_date").is_null() | (pl.col("end_date") >= t0),
        ~pl.col("is_trial"),
    ).with_columns(
        y=(pl.col("end_date").is_not_null() & (pl.col("end_date") < t1)).cast(pl.Int8),
        age_days=(pl.lit(t0) - pl.col("start_date")).dt.total_days(),
    )
    usage = (
        t.feature_usage.filter(pl.col("usage_date") < t0)
        .group_by("subscription_id")
        .agg(
            u_count=pl.col("usage_count").sum(),
            u_errors=pl.col("error_count").sum(),
            u_breadth=pl.col("feature_name").n_unique(),
            u_beta_share=pl.col("is_beta_feature").mean(),
        )
    )
    tickets = (
        t.support_tickets.filter(pl.col("submitted_at") < t0)
        .group_by("account_id")
        .agg(
            t_n=pl.len(),
            t_esc=pl.col("escalation_flag").sum(),
            t_csat=pl.col("satisfaction_score").mean(),
            t_frt=pl.col("first_response_time_minutes").mean(),
            t_res=pl.col("resolution_time_hours").mean(),
        )
    )
    prior = (
        t.churn_events.filter(pl.col("churn_date") < t0)
        .group_by("account_id")
        .agg(prior_churn_events=pl.len())
    )
    accounts = t.accounts.select(
        "account_id",
        "industry",
        "country",
        "referral_source",
        pl.col("seats").alias("acct_seats"),
        (pl.lit(t0) - pl.col("signup_date")).dt.total_days().alias("tenure_days"),
    )
    keep = [
        "subscription_id",
        "account_id",
        "y",
        *NUMERIC_FEATURES,
        *BOOL_FEATURES,
        *CAT_FEATURES,
    ]
    return (
        subs.join(usage, on="subscription_id", how="left")
        .join(tickets, on="account_id", how="left")
        .join(prior, on="account_id", how="left")
        .join(accounts, on="account_id", how="left")
        .with_columns(t_csat_missing=pl.col("t_csat").is_null().cast(pl.Int8))
        .with_columns(pl.col(n).fill_null(0) for n in NUMERIC_FEATURES)
        .select(keep)
        .sort("subscription_id")
    )


def design_matrix(
    panel: pl.DataFrame, categories: dict[str, list[str]] | None = None
) -> tuple[np.ndarray, dict[str, list[str]]]:
    """Matriz numérica + one-hot com as categorias do TREINO (sem vazamento)."""
    if categories is None:
        categories = {c: sorted(panel[c].unique().to_list()) for c in CAT_FEATURES}
    cols = [pl.col(n).cast(pl.Float64) for n in NUMERIC_FEATURES]
    cols += [pl.col(b).cast(pl.Float64) for b in BOOL_FEATURES]
    cols += [
        (pl.col(c) == v).cast(pl.Float64).alias(f"{c}={v}")
        for c, values in categories.items()
        for v in values
    ]
    return panel.select(cols).to_numpy(), categories


# -------------------------------------------------------------------- scorers
class Scorer(Protocol):
    """Qualquer score entra na validação (OCP/LSP)."""

    name: str

    def fit(self, panel: pl.DataFrame) -> Self: ...

    def score(self, panel: pl.DataFrame) -> np.ndarray: ...


@dataclass
class AgeHazardScorer:
    """Risco pela faixa de idade da assinatura (tabela de 5 linhas)."""

    name: str = "idade_da_assinatura"
    rates: dict[str, float] = field(default_factory=dict)
    base: float = 0.0

    def fit(self, panel: pl.DataFrame) -> Self:
        g = (
            panel.with_columns(age_bucket_expr())
            .group_by("age_bucket")
            .agg(r=pl.col("y").mean())
        )
        self.rates = dict(zip(g["age_bucket"], g["r"], strict=True))
        self.base = float(panel["y"].mean())
        return self

    def score(self, panel: pl.DataFrame) -> np.ndarray:
        buckets = panel.with_columns(age_bucket_expr())["age_bucket"].to_list()
        return np.array([self.rates.get(b, self.base) for b in buckets])


@dataclass
class ExpectedLossScorer:
    """Risco × MRR: ordena pelo dinheiro em jogo, não pela probabilidade."""

    inner: AgeHazardScorer = field(default_factory=AgeHazardScorer)
    name: str = "perda_esperada_mrr"

    def fit(self, panel: pl.DataFrame) -> Self:
        self.inner.fit(panel)
        return self

    def score(self, panel: pl.DataFrame) -> np.ndarray:
        return self.inner.score(panel) * panel["mrr_amount"].to_numpy()


@dataclass
class MrrOnlyScorer:
    """Benchmark ingênuo: 'ligue para as maiores contas primeiro'."""

    name: str = "so_mrr"

    def fit(self, panel: pl.DataFrame) -> Self:
        return self

    def score(self, panel: pl.DataFrame) -> np.ndarray:
        return panel["mrr_amount"].to_numpy().astype(float)


@dataclass
class SklearnAllTablesScorer:
    """Benchmark com todas as tabelas (logística ou GBM)."""

    name: str
    kind: str  # "logistic" | "gbm"
    categories: dict[str, list[str]] | None = None
    _model: object | None = None
    _mu: np.ndarray | None = None
    _sd: np.ndarray | None = None

    def _prep(self, x: np.ndarray) -> np.ndarray:
        return (x - self._mu) / self._sd if self.kind == "logistic" else x

    def fit(self, panel: pl.DataFrame) -> Self:
        x, self.categories = design_matrix(panel)
        self._mu, self._sd = x.mean(axis=0), x.std(axis=0) + 1e-9
        model = (
            LogisticRegression(C=0.3, max_iter=5000)
            if self.kind == "logistic"
            else HistGradientBoostingClassifier(
                max_depth=3, learning_rate=0.05, max_iter=200, random_state=SEED
            )
        )
        self._model = model.fit(self._prep(x), panel["y"].to_numpy())
        return self

    def score(self, panel: pl.DataFrame) -> np.ndarray:
        x, _ = design_matrix(panel, self.categories)
        return self._model.predict_proba(self._prep(x))[:, 1]


def default_scorers() -> list[Scorer]:
    return [
        AgeHazardScorer(),
        ExpectedLossScorer(),
        MrrOnlyScorer(),
        SklearnAllTablesScorer(name="logistica_todas_tabelas", kind="logistic"),
        SklearnAllTablesScorer(name="gbm_todas_tabelas", kind="gbm"),
    ]


# ------------------------------------------------------------------ avaliação
def _top_k(score: np.ndarray, mrr: np.ndarray, frac: float) -> np.ndarray:
    """Top-k por score; empate desempata pelo maior MRR (determinístico)."""
    k = max(1, int(round(len(score) * frac)))
    return np.lexsort((-mrr, -score))[:k]


def evaluate(
    y: np.ndarray, score: np.ndarray, mrr: np.ndarray, frac: float = TOP_FRACTION
) -> dict[str, float]:
    idx = _top_k(score, mrr, frac)
    pos, neg = score[y == 1], score[y == 0]
    p_value = (
        float(stats.mannwhitneyu(pos, neg).pvalue) if len(pos) and len(neg) else 1.0
    )
    return {
        "roc_auc": round(float(roc_auc_score(y, score)), 4),
        "pr_auc": round(float(average_precision_score(y, score)), 4),
        "lift_at_10": round(float(y[idx].mean() / y.mean()), 3),
        "mrr_recall_at_10": round(
            float((y[idx] * mrr[idx]).sum() / (y * mrr).sum()), 4
        ),
        "p_value": p_value,
    }


def oot_validation(
    t: Tables,
    train_t0: date = OOT_TRAIN_T0,
    test_t0: date = OOT_TEST_T0,
    horizon_days: int = OOT_HORIZON_DAYS,
    scorers: list[Scorer] | None = None,
) -> pl.DataFrame:
    """Treina no corte antigo, testa no corte novo. Uma linha por score."""
    train = build_oot_panel(t, train_t0, horizon_days)
    test = build_oot_panel(t, test_t0, horizon_days)
    y_tr, y_te = train["y"].to_numpy(), test["y"].to_numpy()
    mrr_tr = train["mrr_amount"].to_numpy().astype(float)
    mrr_te = test["mrr_amount"].to_numpy().astype(float)
    rows = []
    for s in scorers or default_scorers():
        s.fit(train)
        metrics = evaluate(y_te, s.score(test), mrr_te)
        in_sample = evaluate(y_tr, s.score(train), mrr_tr)["roc_auc"]
        rows.append(
            {
                "scorer": s.name,
                **metrics,
                "roc_auc_in_sample": in_sample,
                "n_test": test.height,
                "base_rate": round(float(y_te.mean()), 4),
            }
        )
    return pl.DataFrame(rows)


# ----------------------------------------------------------------- lista do CS
def monthly_hazard_by_age(
    panel: pl.DataFrame, period: str = "target"
) -> dict[str, float]:
    """Risco mensal por faixa de idade no regime mais recente (assinaturas pagas)."""
    h = hazard_table(
        panel.filter(pl.col("period") == period, ~pl.col("is_trial")), ["age_bucket"]
    )
    return dict(zip(h["age_bucket"], h["hazard"], strict=True))


def subscription_risk(
    t: Tables,
    hazards: dict[str, float],
    asof: date = SNAPSHOT_DATE,
    horizon_months: int = RISK_HORIZON_MONTHS,
) -> pl.DataFrame:
    """P(sair em até N meses) envelhecendo a assinatura mês a mês, × MRR pago."""
    active = t.subscriptions.filter(pl.col("end_date").is_null()).with_columns(
        age_days=(pl.lit(asof) - pl.col("start_date")).dt.total_days(),
        paid_mrr=pl.when(pl.col("is_trial")).then(0).otherwise(pl.col("mrr_amount")),
    )
    survival = np.ones(active.height)
    for m in range(horizon_months):
        bucket = age_bucket_expr("_age").replace_strict(hazards, default=0.0)
        step = active.with_columns(_age=pl.col("age_days") + 30 * m).select(bucket)
        survival *= 1 - step.to_series().to_numpy()
    risk = active.with_columns(p_churn=pl.Series(1 - survival).round(5))
    return risk.with_columns(
        expected_loss=(pl.col("p_churn") * pl.col("paid_mrr")).round(2),
        young=pl.col("age_days") < YOUNG_AGE_DAYS,
    )


def _action(rank: int, young_subs: int) -> str:
    if rank <= 10:
        return "CSM sênior: call de ativação em até 7 dias + plano de sucesso"
    if young_subs > 0:
        return "Check-in de onboarding D+7/D+30: confirmar uso das assinaturas novas"
    return "Monitorar: revisão trimestral de conta"


def cs_priority_list(t: Tables, sub_risk: pl.DataFrame, top_n: int) -> pl.DataFrame:
    """Contas ordenadas pela perda esperada de MRR, com motivo e ação."""
    acc = (
        sub_risk.group_by("account_id")
        .agg(
            active_paid_mrr=pl.col("paid_mrr").sum(),
            expected_loss_90d=pl.col("expected_loss").sum().round(0),
            young_subs=(pl.col("young") & (pl.col("paid_mrr") > 0)).sum(),
            young_mrr=pl.col("paid_mrr").filter(pl.col("young")).sum(),
        )
        .join(
            t.accounts.select(
                "account_id", "account_name", "industry", "country", "plan_tier"
            ),
            on="account_id",
        )
        .sort(["expected_loss_90d", "account_id"], descending=[True, False])
        .head(top_n)
        .with_row_index("rank", offset=1)
    )
    return acc.with_columns(
        pct_mrr_at_risk=(
            100 * pl.col("expected_loss_90d") / pl.col("active_paid_mrr")
        ).round(1),
        motivo=pl.format(
            "{} assinatura(s) com <90 dias somando ${} de MRR",
            pl.col("young_subs"),
            pl.col("young_mrr"),
        ),
        acao_sugerida=pl.struct("rank", "young_subs").map_elements(
            lambda r: _action(r["rank"], r["young_subs"]), return_dtype=pl.String
        ),
    ).select(
        "rank",
        "account_id",
        "account_name",
        "industry",
        "country",
        "plan_tier",
        "active_paid_mrr",
        "young_subs",
        "young_mrr",
        "expected_loss_90d",
        "pct_mrr_at_risk",
        "motivo",
        "acao_sugerida",
    )
