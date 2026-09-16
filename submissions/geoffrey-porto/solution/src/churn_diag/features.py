"""Features de taxa e campos em quarentena.

Taxas (proporções) são comparáveis entre contas de tamanhos diferentes; as
contagens brutas não são. A referência (*Features Engineering*) vê sinal nas
taxas — aqui elas são medidas nos dois recortes: janela de 90 dias (como a
referência) e todo o histórico anterior ao corte.

Regra de denominador: **sem denominador, sem taxa** — devolve vazio, nunca zero
(zero diria "nenhum erro", quando o fato é "nenhum uso").
"""

from __future__ import annotations

from datetime import date, timedelta

import polars as pl

from churn_diag.loader import Tables

# Campos sem carimbo de tempo: não há como provar que são anteriores ao corte,
# então não entram em nenhuma matriz de features (P-009).
QUARANTINED_UNDATED: tuple[str, ...] = (
    "upgrade_flag",
    "downgrade_flag",
    "auto_renew_flag",
)

RATE_FEATURES: tuple[str, ...] = (
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
