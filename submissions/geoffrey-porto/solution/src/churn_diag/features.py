"""Features de taxa e campos em quarentena.

Taxas (proporções) são comparáveis entre contas de tamanhos diferentes; as
contagens brutas não são. A referência (*Features Engineering*) vê sinal nas
taxas — aqui elas são medidas nos dois recortes: janela de 90 dias (como a
referência) e todo o histórico anterior ao corte.

Regra de denominador: **sem denominador, sem taxa** — devolve vazio, nunca zero
(zero diria "nenhum erro", quando o fato é "nenhum uso").
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Final

import polars as pl

from churn_diag.loader import Tables

# Campos sem carimbo de tempo: não há como provar que são anteriores ao corte,
# então não entram em nenhuma matriz de features (P-009).
QUARANTINED_UNDATED: Final[tuple[str, ...]] = (
    "upgrade_flag",
    "downgrade_flag",
    "auto_renew_flag",
)

RATE_FEATURES: Final[tuple[str, ...]] = (
    "errors_per_100_uses",
    "escalation_rate",
    "satisfaction_missing_share",
)


def _window_filter(col: str, t0: date, window_days: int | None) -> pl.Expr:
    """Eventos antes do corte; com janela, só os `window_days` anteriores."""
    before = pl.col(col) < t0
    if window_days is None:
        return before
    return before & (pl.col(col) >= t0 - timedelta(days=window_days))


def usage_rates(t: Tables, t0: date, window_days: int | None = None) -> pl.DataFrame:
    """`errors_per_100_uses` por conta (vazio para quem não teve uso na janela)."""
    usage = t.feature_usage.filter(_window_filter("usage_date", t0, window_days)).join(
        t.subscriptions.select("subscription_id", "account_id"),
        on="subscription_id",
        how="inner",
    )
    return (
        usage.group_by("account_id")
        .agg(
            uses=pl.col("usage_count").sum(),
            errors=pl.col("error_count").sum(),
        )
        .with_columns(
            errors_per_100_uses=pl.when(pl.col("uses") > 0)
            .then(100 * pl.col("errors") / pl.col("uses"))
            .otherwise(None)
        )
        .select("account_id", "uses", "errors", "errors_per_100_uses")
        .sort("account_id")
    )


def ticket_rates(t: Tables, t0: date, window_days: int | None = None) -> pl.DataFrame:
    """`escalation_rate` e `satisfaction_missing_share` por conta (vazias sem ticket)."""
    tickets = t.support_tickets.filter(_window_filter("submitted_at", t0, window_days))
    return (
        tickets.group_by("account_id")
        .agg(
            tickets_n=pl.len(),
            escalation_rate=pl.col("escalation_flag").mean(),
            satisfaction_missing_share=pl.col("satisfaction_score").is_null().mean(),
        )
        .sort("account_id")
    )


def rate_features(t: Tables, t0: date, window_days: int | None = None) -> pl.DataFrame:
    """As três taxas da referência, por conta, num corte e recorte de janela."""
    return (
        t.accounts.select("account_id")
        .join(usage_rates(t, t0, window_days), on="account_id", how="left")
        .join(ticket_rates(t, t0, window_days), on="account_id", how="left")
        .select("account_id", "uses", "tickets_n", *RATE_FEATURES)
        .sort("account_id")
    )


def suffixed(window_days: int | None) -> str:
    return "_90d" if window_days else "_all"


# --------------------------------------------- mapa das features da referência
# Registro único do documento *Features Engineering* (docs/referencia/): 20
# features, 8 controles e 3 derivadas. Só dados — o cruzamento com as colunas
# reais dos painéis é feito no teste (evita ciclo de importação).
IMPLEMENTADA: Final[str] = "implementada"
QUARENTENA: Final[str] = "quarentena"
EXCLUIDA_LINHA_DO_TEMPO: Final[str] = "excluida_linha_do_tempo"
NAO_IMPLEMENTADA: Final[str] = "nao_implementada"

STATUS_EMOJI: Final[dict[str, str]] = {
    IMPLEMENTADA: "✅",
    QUARENTENA: "🔒",
    EXCLUIDA_LINHA_DO_TEMPO: "⛔",
    NAO_IMPLEMENTADA: "⬜",
}

SEM_DATA = (
    "flag sem carimbo de tempo: não dá para provar que é anterior ao corte (P-009)"
)
LINHA_DO_TEMPO = (
    "depende da linha do tempo de uso, quebrada neste dataset (ASM-004/ASM-008)"
)
FASE_B = "fase B do plano de completude: ainda não construída"


@dataclass(frozen=True, slots=True)
class ReferenceFeature:
    """Uma entrada do documento da referência e onde ela vive (ou não) aqui."""

    name: str
    source: str
    group: str  # feature | controle | derivada
    status: str
    columns: tuple[tuple[str, str], ...] = ()  # (painel, coluna)
    reason: str = ""


def _f(name: str, source: str, *columns: tuple[str, str]) -> ReferenceFeature:
    return ReferenceFeature(name, source, "feature", IMPLEMENTADA, columns)


def _blocked(name: str, source: str, status: str, reason: str, group: str = "feature"):
    return ReferenceFeature(name, source, group, status, (), reason)


REFERENCE_FEATURES: Final[tuple[ReferenceFeature, ...]] = (
    # --- as 20 features
    _f(
        "tenure_days",
        "accounts",
        ("conta", "tenure_days"),
        ("diagnostico", "tenure_days"),
    ),
    _f("active_mrr", "subscriptions", ("conta", "active_mrr")),
    _f(
        "plan_tier",
        "accounts/subscriptions",
        ("conta", "plan_tier"),
        ("diagnostico", "plan_tier"),
    ),
    _f("active_subscriptions", "subscriptions", ("conta", "active_subscriptions")),
    _f("annual_share", "subscriptions", ("conta", "annual_share")),
    _blocked("auto_renew_share", "subscriptions", QUARENTENA, SEM_DATA),
    _blocked("upgrade_share", "subscriptions", QUARENTENA, SEM_DATA),
    _blocked("downgrade_share", "subscriptions", QUARENTENA, SEM_DATA),
    _f("active_seats", "subscriptions", ("conta", "active_seats")),
    _f("usage_total_90d", "feature_usage", ("conta", "usage_total_90d")),
    _blocked(
        "usage_trend_ratio_90d",
        "feature_usage",
        EXCLUIDA_LINHA_DO_TEMPO,
        LINHA_DO_TEMPO,
    ),
    _blocked(
        "days_since_last_usage",
        "feature_usage",
        EXCLUIDA_LINHA_DO_TEMPO,
        LINHA_DO_TEMPO,
    ),
    _f("feature_breadth_90d", "feature_usage", ("conta", "feature_breadth_90d")),
    _f("usage_duration_90d", "feature_usage", ("conta", "usage_duration_90d")),
    _f(
        "errors_per_100_uses_90d", "feature_usage", ("conta", "errors_per_100_uses_90d")
    ),
    _f("beta_usage_share_90d", "feature_usage", ("conta", "beta_usage_share_90d")),
    _f("tickets_90d", "support_tickets", ("conta", "tickets_90d")),
    _f("escalation_rate_90d", "support_tickets", ("conta", "escalation_rate_90d")),
    _f("response_time_p90_90d", "support_tickets", ("conta", "response_time_p90_90d")),
    _f(
        "satisfaction_missing_share_90d",
        "support_tickets",
        ("conta", "satisfaction_missing_share_90d"),
    ),
    # --- os 8 controles
    ReferenceFeature(
        "industry",
        "accounts",
        "controle",
        IMPLEMENTADA,
        (("conta", "industry"), ("diagnostico", "industry")),
    ),
    ReferenceFeature(
        "country",
        "accounts",
        "controle",
        IMPLEMENTADA,
        (("conta", "country"), ("diagnostico", "country")),
    ),
    ReferenceFeature(
        "referral_source",
        "accounts",
        "controle",
        IMPLEMENTADA,
        (("conta", "referral_source"), ("diagnostico", "referral_source")),
    ),
    ReferenceFeature(
        "is_trial", "accounts", "controle", IMPLEMENTADA, (("conta", "is_trial"),)
    ),
    ReferenceFeature(
        "seats",
        "accounts",
        "controle",
        IMPLEMENTADA,
        (("conta", "seats"), ("diagnostico", "acct_seats")),
    ),
    ReferenceFeature(
        "high_priority_ticket_share_90d",
        "support_tickets",
        "controle",
        IMPLEMENTADA,
        (("conta", "high_priority_ticket_share_90d"),),
    ),
    ReferenceFeature(
        "resolution_time_mean_90d",
        "support_tickets",
        "controle",
        IMPLEMENTADA,
        (("conta", "resolution_time_mean_90d"),),
    ),
    ReferenceFeature(
        "satisfaction_mean_90d",
        "support_tickets",
        "controle",
        IMPLEMENTADA,
        (("conta", "satisfaction_mean_90d"),),
    ),
    # --- as 3 derivadas
    ReferenceFeature(
        "usage_per_active_seat_90d",
        "feature_usage/subscriptions",
        "derivada",
        IMPLEMENTADA,
        (("conta", "usage_per_active_seat_90d"),),
    ),
    ReferenceFeature(
        "support_friction_index",
        "support_tickets",
        "derivada",
        IMPLEMENTADA,
        (("conta", "support_friction_index"),),
    ),
    _blocked(
        "commercial_contraction_flag",
        "subscriptions",
        QUARENTENA,
        "depende de downgrade_share e auto_renew_share, ambas em quarentena (P-009)",
        group="derivada",
    ),
)


def reference_counts() -> dict[str, int]:
    """Quantas features da referência em cada status (usado no documento)."""
    counts: dict[str, int] = {}
    for f in REFERENCE_FEATURES:
        counts[f.status] = counts.get(f.status, 0) + 1
    return counts


# ------------------------------------------------- derivadas da referência (B)
# Duas features compostas sugeridas pelo documento da referência. A terceira
# (`commercial_contraction_flag`) depende de flags em quarentena e não é
# construível com integridade.
FRICTION_COMPONENTS: Final[tuple[str, ...]] = (
    "tickets_90d",
    "escalation_rate_90d",
    "response_time_p90_90d",
    "high_priority_ticket_share_90d",
)
DERIVED_FEATURES: Final[tuple[str, ...]] = (
    "usage_per_active_seat_90d",
    "support_friction_index",
)


def usage_per_active_seat_expr() -> pl.Expr:
    """Uso da janela ÷ assentos ativos (mínimo 1), como na referência.

    Conta sem uso na janela recebe **zero** — "não usou" é informação, não
    ausência de dado (diferente das taxas, onde falta o denominador).
    """
    seats = pl.max_horizontal(pl.col("active_seats"), pl.lit(1))
    return (pl.col("usage_total_90d").fill_null(0) / seats).alias(
        "usage_per_active_seat_90d"
    )


def zscore_stats(
    train: pl.DataFrame, columns: tuple[str, ...] = FRICTION_COMPONENTS
) -> dict[str, tuple[float, float]]:
    """Média e desvio de cada componente, **só do treino** (evita vazamento)."""
    stats: dict[str, tuple[float, float]] = {}
    for col in columns:
        series = train[col].drop_nulls()
        mean = float(series.mean()) if series.len() else 0.0
        std = float(series.std()) if series.len() > 1 else 0.0
        stats[col] = (mean, std if std and std > 0 else 1.0)
    return stats


def support_friction_expr(stats: dict[str, tuple[float, float]]) -> pl.Expr:
    """Soma dos z-scores de atrito; vazio quando a conta não teve ticket.

    As quatro componentes faltam em bloco (ASM-012), então basta uma guarda:
    sem ticket na janela, não existe índice de atrito — e zero diria
    "atrito médio", que é outra coisa.
    """
    total = None
    for col in FRICTION_COMPONENTS:
        mean, std = stats[col]
        z = (pl.col(col) - mean) / std
        total = z if total is None else total + z
    return (
        pl.when(pl.col("tickets_90d").is_null())
        .then(None)
        .otherwise(total)
        .alias("support_friction_index")
    )


def attach_derived_features(
    panel: pl.DataFrame, stats: dict[str, tuple[float, float]]
) -> pl.DataFrame:
    """Acrescenta as duas derivadas ao painel, com os parâmetros dados."""
    return panel.with_columns(
        usage_per_active_seat_expr(), support_friction_expr(stats)
    )
