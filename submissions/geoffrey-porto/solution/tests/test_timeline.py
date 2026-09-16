from __future__ import annotations

from datetime import date

import polars as pl
from fixtures import make_tables, sub

from churn_diag.account_panel import (
    ACCOUNT_CATEGORICAL,
    ACCOUNT_NUMERIC,
    TIMELINE_COLUMNS,
    attach_timeline_features,
    build_account_panel,
    split_train_test,
)
from churn_diag.config import SOLUTION_ROOT
from churn_diag.features import (
    MEDIDA_SOB_BANDEIRA,
    QUARENTENA,
    REFERENCE_FEATURES,
    TIMELINE_UNRELIABLE,
    consistent_usage,
    timeline_features,
)
from churn_diag.loader import Tables
from churn_diag.risk import (
    CAT_FEATURES,
    NUMERIC_FEATURES,
    cs_priority_list,
    subscription_risk,
)
from churn_diag.screening import univariate_screening

T0 = date(2024, 10, 1)


def _tables():
    """A-1 usa dentro da janela da assinatura; A-2 usa fora dela (dado inconsistente)."""
    return make_tables(
        accounts=[{"account_id": "A-1"}, {"account_id": "A-2"}],
        subscriptions=[
            sub("S-1", date(2024, 1, 1), None, account_id="A-1"),
            sub("S-2", date(2024, 9, 20), None, account_id="A-2"),
        ],
        feature_usage=[
            # A-1: 10 usos na 1ª metade da janela, 30 na 2ª -> tendência 31/11
            {
                "usage_id": "U-1",
                "subscription_id": "S-1",
                "usage_date": date(2024, 7, 20),
                "usage_count": 10,
            },
            {
                "usage_id": "U-2",
                "subscription_id": "S-1",
                "usage_date": date(2024, 9, 15),
                "usage_count": 30,
            },
            # A-2: uso ANTES do início da assinatura (inconsistente)
            {
                "usage_id": "U-3",
                "subscription_id": "S-2",
                "usage_date": date(2024, 7, 10),
                "usage_count": 50,
            },
        ],
    )


def test_trend_and_recency_in_the_raw_cut() -> None:
    """@spec:AC-031 — tendência pela fórmula da referência e dias desde o último uso."""
    out = timeline_features(_tables(), T0)
    a1 = out.filter(pl.col("account_id") == "A-1").row(0, named=True)
    assert a1["usage_trend_ratio_90d_bruto"] == (30 + 1) / (10 + 1)
    assert a1["days_since_last_usage_bruto"] == 16  # 2024-09-15 -> 2024-10-01
    assert "A-2" in out["account_id"].to_list()  # o dado inconsistente entra no bruto


def test_consistent_cut_drops_usage_outside_the_subscription() -> None:
    """@spec:AC-031 — no recorte consistente, uso fora da janela da assinatura sai."""
    t = _tables()
    assert consistent_usage(t).height == 2  # os dois eventos de A-1
    out = timeline_features(t, T0, consistent=True)
    assert out["account_id"].to_list() == ["A-1"]
    assert out.columns == [
        "account_id",
        "usage_trend_ratio_90d_consistente",
        "days_since_last_usage_consistente",
    ]


def test_account_without_usage_in_the_window_is_absent() -> None:
    """@spec:AC-031 — sem uso no recorte, a conta não recebe valor inventado."""
    t = make_tables(
        accounts=[{"account_id": "A-9"}],
        subscriptions=[sub("S-9", date(2024, 1, 1), None, account_id="A-9")],
    )
    assert timeline_features(t, T0).height == 0


def test_unreliable_list_is_declared_once() -> None:
    """@spec:AC-032 — a lista de features não confiáveis mora num lugar só."""
    assert TIMELINE_UNRELIABLE == ("usage_trend_ratio_90d", "days_since_last_usage")


def test_timeline_features_never_reach_the_score_or_the_replication(
    real_tables: Tables,
) -> None:
    """@spec:AC-032 @principle:P-009 — bandeira vermelha: fora do score e da replicação."""
    proibidas = set(TIMELINE_COLUMNS) | set(TIMELINE_UNRELIABLE)
    # replicação da referência
    assert not proibidas & (set(ACCOUNT_NUMERIC) | set(ACCOUNT_CATEGORICAL))
    # painel do diagnóstico (base do score)
    assert not proibidas & (set(NUMERIC_FEATURES) | set(CAT_FEATURES))
    # lista do CS, que é o que a operação usa
    hazards = {
        "0-30d": 0.05,
        "30-90d": 0.02,
        "90-180d": 0.01,
        "180-365d": 0.01,
        "365d+": 0.01,
    }
    risco = subscription_risk(real_tables, hazards)
    cs = cs_priority_list(real_tables, risco, top_n=5)
    assert not proibidas & set(cs.columns)


def test_both_cuts_are_screened_separately(real_tables: Tables) -> None:
    """@spec:AC-033 — quatro medições: duas features × dois recortes."""
    panel = attach_timeline_features(real_tables, build_account_panel(real_tables))
    _, test = split_train_test(panel)
    out = univariate_screening(test, list(TIMELINE_COLUMNS))
    assert out.height == 4
    assert {"_bruto", "_consistente"} <= {
        "_bruto" if f.endswith("_bruto") else "_consistente" for f in out["feature"]
    }
    assert out["p_holm"].is_between(0, 1).all()


def test_contract_covers_every_blocked_item() -> None:
    """@spec:AC-034 — nada fica bloqueado sem pedido de dado correspondente."""
    contrato = (SOLUTION_ROOT.parent / "docs" / "05-contrato-de-dados.md").read_text(
        encoding="utf-8"
    )
    bloqueados = [
        f for f in REFERENCE_FEATURES if f.status in (QUARENTENA, MEDIDA_SOB_BANDEIRA)
    ]
    assert len(bloqueados) == 6
    linhas = [
        [c.strip() for c in ln.strip("|").split("|")]
        for ln in contrato.splitlines()
        if ln.startswith("|")
    ]
    itens = {celulas[0]: celulas for celulas in linhas}
    for f in bloqueados:
        celulas = itens.get(f"`{f.name}`")
        assert celulas is not None, f"{f.name} não aparece no contrato"
        assert len(celulas) == 4, f"{f.name}: contrato sem as 4 colunas"
        assert all(celulas), f"{f.name}: coluna vazia no contrato"
