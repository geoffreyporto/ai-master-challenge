"""Registro de hipóteses: cada explicação sai com teste, efeito e rótulo.

Rótulos (P-004):
- `descricao`       — o que aconteceu (fato medido);
- `predicao`        — o que tende a acontecer com uma conta (score);
- `hipotese_causal` — "se fizermos X, o churn cai" — sempre com o experimento
  que a validaria, porque dado observacional não prova causa.

Adicionar uma hipótese = escrever uma função `(Context) -> Finding` e colocá-la
em REGISTRY. O executor não muda (OCP).
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass, replace
from typing import Literal

import numpy as np
import polars as pl
from scipy import stats

from churn_diag.config import YOUNG_AGE_DAYS
from churn_diag.loader import Tables
from churn_diag.metrics import standardized_ratio
from churn_diag.quality import cramers_v

ClaimType = Literal["descricao", "predicao", "hipotese_causal"]
CLAIM_TYPES: tuple[str, ...] = ("descricao", "predicao", "hipotese_causal")
ALPHA = 0.05


@dataclass(frozen=True, slots=True)
class Finding:
    id: str
    title: str
    claim_type: ClaimType
    tables: tuple[str, ...]
    test: str
    statistic: float
    p_value: float
    effect_name: str
    effect: float
    detail: str
    validation: str | None = None
    p_holm: float | None = None

    @property
    def significant(self) -> bool:
        p = self.p_holm if self.p_holm is not None else self.p_value
        return bool(p < ALPHA)

    def as_row(self) -> dict[str, object]:
        row = asdict(self)
        row["tables"] = "+".join(self.tables)
        row["significant"] = self.significant
        for k in ("statistic", "effect"):
            row[k] = round(float(row[k]), 4)
        for k in ("p_value", "p_holm"):
            row[k] = float(f"{row[k]:.3g}") if row[k] is not None else None
        return row


@dataclass(frozen=True, slots=True)
class Context:
    """Tudo que as hipóteses podem consultar (injeção de dependência)."""

    tables: Tables
    panel: pl.DataFrame
    oot: pl.DataFrame | None = None  # resultado da validação fora do tempo


def holm(p_values: Sequence[float]) -> list[float]:
    """Correção de Holm (step-down), com monotonicidade e teto em 1."""
    p = np.asarray(p_values, dtype=float)
    order = np.argsort(p)
    m = len(p)
    adjusted = np.empty(m)
    running = 0.0
    for rank, idx in enumerate(order):
        running = max(running, min(1.0, (m - rank) * p[idx]))
        adjusted[idx] = running
    return adjusted.tolist()


# --------------------------------------------------------------------- helpers
def _target_accounts(ctx: Context) -> pl.DataFrame:
    """Contas ativas no 4º tri com rótulo: perdeu ≥1 assinatura paga no tri."""
    tgt = ctx.panel.filter(pl.col("period") == "target", ~pl.col("is_trial"))
    return tgt.group_by("account_id").agg(lost=pl.col("ended").any())


def _auc(pos: np.ndarray, neg: np.ndarray) -> tuple[float, float]:
    u, p = stats.mannwhitneyu(pos, neg, alternative="two-sided")
    return float(u / (len(pos) * len(neg))), float(p)


def _log_rr_var(a: int, n1: int, c: int, n2: int) -> float:
    return 1 / a - 1 / n1 + 1 / c - 1 / n2


# ------------------------------------------------------------------ hypotheses
def h1_rate_rise_beyond_mix(ctx: Context) -> Finding:
    s = standardized_ratio(ctx.panel)
    return Finding(
        id="H1",
        title="O churn do 4º tri/2024 subiu além do que o mix de idade explica",
        claim_type="descricao",
        tables=("subscriptions",),
        test="Poisson exato: observado ≥ esperado (risco de referência por idade)",
        statistic=float(s["observed"]),
        p_value=s["p_value"],
        effect_name="observado/esperado",
        effect=s["ratio"],
        detail=f"{s['observed']} saídas vs {s['expected']} esperadas; "
        f"MRR {s['mrr_observed']:,.0f} vs {s['mrr_expected']:,.0f}",
    )


def h2_concentrated_in_young(ctx: Context) -> Finding:
    p = ctx.panel.filter(pl.col("period").is_in(["reference", "target"]))
    p = p.with_columns(young=pl.col("age_days") < YOUNG_AGE_DAYS)
    g = p.group_by("period", "young").agg(n=pl.len(), e=pl.col("ended").sum())
    get = {(r["period"], r["young"]): (r["e"], r["n"]) for r in g.iter_rows(named=True)}
    (ey_t, ny_t), (ey_r, ny_r) = get[("target", True)], get[("reference", True)]
    (em_t, nm_t), (em_r, nm_r) = get[("target", False)], get[("reference", False)]
    rr_young = (ey_t / ny_t) / (ey_r / ny_r)
    rr_mature = (em_t / nm_t) / (em_r / nm_r)
    z = (np.log(rr_young) - np.log(rr_mature)) / np.sqrt(
        _log_rr_var(ey_t, ny_t, ey_r, ny_r) + _log_rr_var(em_t, nm_t, em_r, nm_r)
    )
    return Finding(
        id="H2",
        title="A alta está concentrada em assinaturas com menos de 90 dias",
        claim_type="descricao",
        tables=("subscriptions",),
        test="z para diferença de log(RR) jovem vs madura (4º tri vs referência)",
        statistic=float(z),
        p_value=float(2 * stats.norm.sf(abs(z))),
        effect_name="RR jovem ÷ RR madura",
        effect=float(rr_young / rr_mature),
        detail=f"RR jovem {rr_young:.2f}× · RR madura {rr_mature:.2f}×",
    )


def h3_csat_does_not_separate(ctx: Context) -> Finding:
    acc = _target_accounts(ctx)
    csat = ctx.tables.support_tickets.group_by("account_id").agg(
        csat=pl.col("satisfaction_score").mean()
    )
    d = acc.join(csat, on="account_id", how="inner").drop_nulls("csat")
    auc, p = _auc(
        d.filter(pl.col("lost"))["csat"].to_numpy(),
        d.filter(~pl.col("lost"))["csat"].to_numpy(),
    )
    return Finding(
        id="H3",
        title="A satisfação (CSAT) não distingue quem perdeu receita de quem ficou",
        claim_type="descricao",
        tables=("support_tickets", "subscriptions", "accounts"),
        test="Mann-Whitney: CSAT médio por conta, perdeu MRR no 4º tri vs não",
        statistic=auc,
        p_value=p,
        effect_name="AUC (0,5 = acaso)",
        effect=auc,
        detail=f"{d.height} contas com CSAT; nulos = não responderam",
    )


def h4_usage_did_not_grow(ctx: Context) -> Finding:
    usage = (
        ctx.tables.feature_usage.filter(pl.col("usage_date").dt.year() == 2024)
        .group_by(pl.col("usage_date").dt.truncate("1mo").alias("month"))
        .agg(usage=pl.col("usage_count").sum())
    )
    active = (
        ctx.panel.filter(pl.col("month").dt.year() == 2024)
        .group_by("month")
        .agg(active=pl.len())
    )
    m = usage.join(active, on="month").sort("month")
    rho, p = stats.spearmanr(np.arange(m.height), m["usage"].to_numpy())
    per_sub = (m["usage"] / m["active"]).to_numpy()
    change = per_sub[-1] / per_sub[0] - 1
    return Finding(
        id="H4",
        title="O uso não cresceu: total estável enquanto a base ativa cresceu",
        claim_type="descricao",
        tables=("feature_usage", "subscriptions"),
        test="Spearman: tendência do uso total mensal em 2024",
        statistic=float(rho),
        p_value=float(p),
        effect_name="variação do uso por assinatura ativa (jan→dez)",
        effect=float(change),
        detail=f"uso/mês {int(m['usage'].min()):,}–{int(m['usage'].max()):,}; "
        f"assinaturas ativas {int(m['active'][0]):,}→{int(m['active'][-1]):,}",
    )


def h5_behaviour_does_not_predict(ctx: Context) -> Finding:
    if ctx.oot is None:
        raise ValueError("H5 precisa do resultado da validação fora do tempo")
    row = ctx.oot.filter(pl.col("scorer") == "gbm_todas_tabelas").row(0, named=True)
    return Finding(
        id="H5",
        title="Uso, suporte e satisfação não preveem o churn fora do tempo",
        claim_type="predicao",
        tables=(
            "accounts",
            "subscriptions",
            "feature_usage",
            "support_tickets",
            "churn_events",
        ),
        test="Validação fora do tempo (treino jul/24 → teste out/24); Mann-Whitney",
        statistic=float(row["roc_auc"]),
        p_value=float(row["p_value"]),
        effect_name="ROC-AUC fora do tempo",
        effect=float(row["roc_auc"]),
        detail=f"ROC dentro da amostra {row['roc_auc_in_sample']:.2f} → fora "
        f"{row['roc_auc']:.2f}: o modelo decorou ruído",
    )


def h6_support_reason_not_in_tickets(ctx: Context) -> Finding:
    reasons = ctx.tables.churn_events.group_by("account_id").agg(
        said_support=(pl.col("reason_code") == "support").any()
    )
    tickets = ctx.tables.support_tickets.group_by("account_id").agg(
        friction=pl.len() + pl.col("escalation_flag").sum() * 2
    )
    d = reasons.join(tickets, on="account_id", how="left").fill_null(0)
    auc, p = _auc(
        d.filter(pl.col("said_support"))["friction"].to_numpy(),
        d.filter(~pl.col("said_support"))["friction"].to_numpy(),
    )
    return Finding(
        id="H6",
        title="Quem declarou 'suporte' como motivo não teve mais atrito no suporte",
        claim_type="descricao",
        tables=("churn_events", "support_tickets"),
        test="Mann-Whitney: tickets + 2×escalações, motivo 'support' vs outros",
        statistic=auc,
        p_value=p,
        effect_name="AUC (0,5 = acaso)",
        effect=auc,
        detail=f"{int(d['said_support'].sum())} contas declararam 'support'",
    )


def h7_reason_vs_feedback(ctx: Context) -> Finding:
    tab = (
        ctx.tables.churn_events.drop_nulls("feedback_text")
        .group_by("reason_code", "feedback_text")
        .len()
        .pivot(on="feedback_text", index="reason_code", values="len")
        .fill_null(0)
        .sort("reason_code")
    )
    chi2, p, v = cramers_v(tab.drop("reason_code").to_numpy())
    return Finding(
        id="H7",
        title="O motivo codificado e o comentário do cliente não concordam",
        claim_type="descricao",
        tables=("churn_events",),
        test="Qui-quadrado motivo × comentário",
        statistic=chi2,
        p_value=p,
        effect_name="V de Cramér (0 = independentes)",
        effect=v,
        detail="ex.: motivo 'pricing' com comentário 'missing features'",
    )


def h8_volume_surge_early_churn(ctx: Context) -> Finding:
    p = ctx.panel.filter(pl.col("month").dt.year() == 2024)
    starts = (
        ctx.tables.subscriptions.filter(pl.col("start_date").dt.year() == 2024)
        .group_by(pl.col("start_date").dt.truncate("1mo").alias("month"))
        .agg(starts=pl.len())
    )
    early = (
        p.filter(pl.col("age_bucket") == "0-30d")
        .group_by("month")
        .agg(h=pl.col("ended").mean())
    )
    m = starts.join(early, on="month").sort("month")
    rho, pv = stats.spearmanr(m["starts"].to_numpy(), m["h"].to_numpy())
    firsts = ctx.tables.subscriptions.group_by("account_id").agg(
        first=pl.col("start_date").min()
    )
    return Finding(
        id="H8",
        title="O salto de novas assinaturas no 4º tri trouxe assinaturas que não "
        "se sustentam (onboarding/encaixe)",
        claim_type="hipotese_causal",
        tables=("subscriptions", "accounts"),
        test="Spearman: novas assinaturas/mês vs risco dos primeiros 30 dias (2024)",
        statistic=float(rho),
        p_value=float(pv),
        effect_name="rho de Spearman",
        effect=float(rho),
        detail=f"{firsts.height} contas; ambas as séries sobem no tempo — "
        "tendência comum pode explicar a correlação",
        validation="Teste A/B de onboarding D+7/D+30 em novas assinaturas "
        "Pro/Enterprise + auditoria de 20 cancelamentos de dez/24 no billing",
    )


def _segment_finding(ctx: Context, hid: str, col: str, label: str) -> Finding:
    tgt = ctx.panel.filter(pl.col("period") == "target", ~pl.col("is_trial"))
    subs = tgt.group_by("subscription_id", "account_id").agg(lost=pl.col("ended").any())
    seg_col = f"acct_{col}" if col == "plan_tier" else col
    acc = ctx.tables.accounts.select("account_id", pl.col(col).alias(seg_col))
    d = subs.join(acc, on="account_id")
    tab = (
        d.group_by(seg_col, "lost")
        .len()
        .pivot(on="lost", index=seg_col, values="len")
        .fill_null(0)
        .sort(seg_col)
    )
    chi2, p, v = cramers_v(tab.drop(seg_col).to_numpy())
    rates = d.group_by(seg_col).agg(r=pl.col("lost").mean()).sort("r")
    return Finding(
        id=hid,
        title=f"{label} não diferencia o churn do 4º tri",
        claim_type="descricao",
        tables=("subscriptions", "accounts"),
        test=f"Qui-quadrado {label.lower()} × saiu no 4º tri (assinaturas pagas)",
        statistic=chi2,
        p_value=p,
        effect_name="V de Cramér",
        effect=v,
        detail=f"de {100 * rates['r'][0]:.1f}% ({rates[seg_col][0]}) a "
        f"{100 * rates['r'][-1]:.1f}% ({rates[seg_col][-1]})",
    )


def h9_industry(ctx: Context) -> Finding:
    return _segment_finding(ctx, "H9", "industry", "Indústria")


def h10_country(ctx: Context) -> Finding:
    return _segment_finding(ctx, "H10", "country", "País")


def h11_channel(ctx: Context) -> Finding:
    return _segment_finding(ctx, "H11", "referral_source", "Canal de aquisição")


def h12_plan(ctx: Context) -> Finding:
    return _segment_finding(ctx, "H12", "plan_tier", "Plano inicial da conta")


REGISTRY: tuple[Callable[[Context], Finding], ...] = (
    h1_rate_rise_beyond_mix,
    h2_concentrated_in_young,
    h3_csat_does_not_separate,
    h4_usage_did_not_grow,
    h5_behaviour_does_not_predict,
    h6_support_reason_not_in_tickets,
    h7_reason_vs_feedback,
    h8_volume_surge_early_churn,
    h9_industry,
    h10_country,
    h11_channel,
    h12_plan,
)


def run_all(
    ctx: Context, registry: Sequence[Callable[[Context], Finding]] = REGISTRY
) -> list[Finding]:
    """Roda o registro e aplica Holm sobre todas as hipóteses juntas."""
    findings = [h(ctx) for h in registry]
    adjusted = holm([f.p_value for f in findings])
    return [replace(f, p_holm=p) for f, p in zip(findings, adjusted, strict=True)]


def findings_frame(findings: Sequence[Finding]) -> pl.DataFrame:
    return pl.DataFrame([f.as_row() for f in findings])


# ----------------------------------------------------------------- invariância
ENV_TYPES: tuple[str, ...] = ("industry", "plan_tier", "referral_source", "periodo")


def invariance_table(tables: Tables, panel: pl.DataFrame) -> pl.DataFrame:
    """Razão de risco jovem (<90d) ÷ madura por ambiente, em 2024.

    Se a direção se mantém em todos os ambientes, a relação é *estável* —
    requisito para chamá-la de candidata causal (não prova de causa).

    A quebra de set–out/2024 entra como ambiente (`periodo`: antes/depois), não
    como causa identificada — decisão do dono do produto enquanto Q-001 não é
    respondida (ASM-006).
    """
    p = panel.filter(pl.col("month") >= pl.date(2024, 1, 1)).join(
        tables.accounts.select("account_id", "industry", "referral_source"),
        on="account_id",
    )
    p = p.with_columns(
        young=pl.col("age_days") < YOUNG_AGE_DAYS,
        periodo=pl.when(pl.col("period") == "target")
        .then(pl.lit("depois (out-dez/24)"))
        .otherwise(pl.lit("antes (jan-set/24)")),
    )
    rows = []
    for env_type in ENV_TYPES:
        g = p.group_by(env_type, "young").agg(n=pl.len(), e=pl.col("ended").sum())
        for env in sorted(g[env_type].unique().to_list()):
            sub = {
                r["young"]: (r["e"], r["n"])
                for r in g.filter(pl.col(env_type) == env).iter_rows(named=True)
            }
            (a, n1), (c, n2) = sub[True], sub[False]
            hr = (a / n1) / (c / n2)
            se = np.sqrt(_log_rr_var(a, n1, c, n2))
            rows.append(
                {
                    "env_type": env_type,
                    "env": env,
                    "exposures": n1 + n2,
                    "hazard_young": round(a / n1, 5),
                    "hazard_mature": round(c / n2, 5),
                    "hr": round(hr, 3),
                    "ci_low": round(float(np.exp(np.log(hr) - 1.96 * se)), 3),
                    "ci_high": round(float(np.exp(np.log(hr) + 1.96 * se)), 3),
                }
            )
    out = pl.DataFrame(rows).with_columns(
        direction=pl.when(pl.col("hr") > 1).then(pl.lit("+")).otherwise(pl.lit("-")),
        ci_excludes_1=pl.col("ci_low") > 1,
    )
    return out.with_columns(
        stable_in_type=(pl.col("direction") == "+").all().over("env_type")
    )
