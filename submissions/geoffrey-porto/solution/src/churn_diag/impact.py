"""Impacto estimado em MRR e desenho do teste A/B.

"Impacto" aqui é o excesso de MRR perdido no 4º tri acima do que o risco de
referência por idade prevê. Recuperar parte dele é uma HIPÓTESE (P-004): o
número diz quanto está em jogo, não quanto a ação vai devolver — por isso o
teste A/B vem junto.
"""

from __future__ import annotations

import math

import polars as pl
from scipy import stats

from churn_diag.config import RECOVERY_SCENARIOS
from churn_diag.metrics import standardized_ratio


def excess_mrr(panel: pl.DataFrame, months_in_target: int = 3) -> dict[str, float]:
    """MRR perdido no alvo acima do esperado pelo risco de referência por idade."""
    s = standardized_ratio(panel)
    excess = max(0.0, s["mrr_observed"] - s["mrr_expected"])
    return {
        "mrr_lost_target": s["mrr_observed"],
        "mrr_expected_target": s["mrr_expected"],
        "excess_mrr_target": round(excess, 0),
        "excess_mrr_per_month": round(excess / months_in_target, 0),
    }


def recovery_scenarios(
    excess_per_month: float, reductions: tuple[float, ...] = RECOVERY_SCENARIOS
) -> dict[str, dict[str, float]]:
    """MRR preservado por mês e ARR equivalente, por cenário de redução."""
    out = {}
    for r in reductions:
        mrr = round(excess_per_month * r, 0)
        out[f"{int(r * 100)}pct"] = {"mrr_per_month": mrr, "arr_equivalent": mrr * 12}
    return out


def ab_sample_size(
    p0: float, p1: float, alpha: float = 0.05, power: float = 0.80
) -> int:
    """n por braço — teste bilateral de duas proporções (fórmula clássica)."""
    if not (0 < p0 < 1 and 0 < p1 < 1) or p0 == p1:
        raise ValueError("p0 e p1 devem estar em (0, 1) e ser diferentes")
    z_a = stats.norm.ppf(1 - alpha / 2)
    z_b = stats.norm.ppf(power)
    p_bar = (p0 + p1) / 2
    num = z_a * math.sqrt(2 * p_bar * (1 - p_bar)) + z_b * math.sqrt(
        p0 * (1 - p0) + p1 * (1 - p1)
    )
    return math.ceil(num**2 / (p0 - p1) ** 2)


def ab_test_design(panel: pl.DataFrame, reduction: float = 0.5) -> dict[str, float]:
    """Desenho do teste de onboarding: controle = risco dos primeiros 30 dias no 4º tri."""
    tgt = panel.filter(pl.col("period") == "target", ~pl.col("is_trial"))
    young = tgt.filter(pl.col("age_bucket") == "0-30d")
    p0 = float(young["ended"].mean())
    p1 = p0 * (1 - reduction)
    n = ab_sample_size(p0, p1)
    new_per_month = young.filter(pl.col("age_days") == 0).height / 3  # iniciadas/mês
    weeks = 2 * n / new_per_month * 52 / 12 if new_per_month else float("inf")
    return {
        "p0_first_30d": round(p0, 4),
        "p1_target": round(p1, 4),
        "n_per_arm": n,
        "new_paid_subs_per_month": round(new_per_month, 0),
        "weeks_to_enroll": round(weeks, 1),
    }
