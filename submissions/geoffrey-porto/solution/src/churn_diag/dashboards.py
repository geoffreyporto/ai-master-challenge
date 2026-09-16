"""Painéis por stakeholder — só o que as cinco tabelas sustentam.

Cada painel tem os quatro níveis de análise (descritivo, diagnóstico, preditivo,
prescritivo) e uma lista explícita de **lacunas**: KPIs que o stakeholder pediria
e que este conjunto de dados não permite calcular (CAC, LTV com margem, verba de
mídia, logins, descontos). Inventar esses números seria o erro mais caro que um
painel pode cometer — ele parece certo até alguém decidir com ele.

A saída é um único JSON consumido pela página em `dashboard/`.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

import polars as pl

from churn_diag.config import SNAPSHOT_DATE, TARGET_START
from churn_diag.loader import Tables
from churn_diag.metrics import exposure_panel, monthly_churn, period_expr

NIVEIS = ("descritivo", "diagnostico", "preditivo", "prescritivo")
STAKEHOLDERS = ("ceo", "vendas", "marketing", "financeiro", "operacoes")

# Aviso reaproveitado: as duas tabelas com carimbo de tempo quebrado.
AVISO_USO = (
    "76,6% dos eventos de uso têm data anterior ao início da assinatura; "
    "leia como ordem de grandeza, não como série temporal."
)
AVISO_TICKETS = (
    "53,9% dos tickets têm data anterior ao cadastro da conta; "
    "volumes valem, a cronologia não."
)


def _kpi(
    rotulo: str,
    valor: float,
    *,
    unidade: str = "",
    nota: str = "",
    direcao: str = "neutro",
    chave: str = "",
) -> dict[str, Any]:
    return {
        "rotulo": rotulo,
        "valor": valor,
        "unidade": unidade,
        "nota": nota,
        "direcao": direcao,
        "chave": chave,
    }


def _br(valor: float, casas: int = 0) -> str:
    """Número em pt-BR: milhar com ponto, decimal com vírgula."""
    texto = f"{valor:,.{casas}f}"
    return texto.replace(",", "§").replace(".", ",").replace("§", ".")


def _lacuna(kpi: str, porque: str) -> dict[str, str]:
    return {"kpi": kpi, "porque": porque}


# ------------------------------------------------------------------ agregados
def mrr_por_plano(t: Tables, asof: date = SNAPSHOT_DATE) -> pl.DataFrame:
    """MRR ativo e assinaturas ativas por plano, no snapshot."""
    ativos = t.subscriptions.filter(
        pl.col("start_date") <= asof,
        pl.col("end_date").is_null() | (pl.col("end_date") > asof),
        ~pl.col("is_trial"),
    )
    return (
        ativos.group_by("plan_tier")
        .agg(
            mrr=pl.col("mrr_amount").sum(),
            assinaturas=pl.len(),
            mrr_medio=pl.col("mrr_amount").mean().round(2),
        )
        .sort("mrr", descending=True)
    )


def saidas_por_dimensao(t: Tables, dimensao: str) -> pl.DataFrame:
    """Saídas e MRR perdido por dimensão da conta, no período-alvo."""
    encerradas = (
        t.subscriptions.filter(
            pl.col("end_date").is_not_null(), ~pl.col("is_trial")
        ).join(t.accounts.select("account_id", dimensao), on="account_id", how="left")
    ).with_columns(period_expr("end_date"))
    return (
        encerradas.group_by(dimensao)
        .agg(
            saidas_total=pl.len(),
            saidas_alvo=(pl.col("period") == "target").sum(),
            mrr_perdido_alvo=pl.col("mrr_amount")
            .filter(pl.col("period") == "target")
            .sum()
            .round(0),
        )
        .sort("mrr_perdido_alvo", descending=True)
    )


def base_por_canal(t: Tables) -> pl.DataFrame:
    """Aquisição por canal: contas, MRR ativo, churn de assinatura e precoce."""
    subs = t.subscriptions.filter(~pl.col("is_trial")).join(
        t.accounts.select("account_id", "referral_source"), on="account_id", how="left"
    )
    ativo = subs.filter(pl.col("end_date").is_null())
    encerrado = subs.filter(pl.col("end_date").is_not_null()).with_columns(
        dias_ate_sair=(pl.col("end_date") - pl.col("start_date")).dt.total_days()
    )
    canais = (
        subs.group_by("referral_source")
        .agg(assinaturas=pl.len(), contas=pl.col("account_id").n_unique())
        .join(
            ativo.group_by("referral_source").agg(mrr_ativo=pl.col("mrr_amount").sum()),
            on="referral_source",
            how="left",
        )
        .join(
            encerrado.group_by("referral_source").agg(
                saidas=pl.len(),
                saidas_ate_90d=(pl.col("dias_ate_sair") <= 90).sum(),
                duracao_mediana=pl.col("dias_ate_sair").median(),
            ),
            on="referral_source",
            how="left",
        )
        .fill_null(0)
    )
    return canais.with_columns(
        churn_pct=(100 * pl.col("saidas") / pl.col("assinaturas")).round(1),
        precoce_pct=(
            100 * pl.col("saidas_ate_90d") / pl.col("saidas").replace(0, None)
        ).round(1),
        receita_observada=(pl.col("duracao_mediana") / 30).round(1),
    ).sort("mrr_ativo", descending=True)


def reembolsos_por_motivo(t: Tables) -> pl.DataFrame:
    """Reembolso emitido por motivo declarado de churn."""
    return (
        t.churn_events.group_by("reason_code")
        .agg(
            eventos=pl.len(),
            reembolso_total=pl.col("refund_amount_usd").sum().round(2),
            reembolso_medio=pl.col("refund_amount_usd").mean().round(2),
            com_reembolso=(pl.col("refund_amount_usd") > 0).sum(),
        )
        .sort("reembolso_total", descending=True)
    )


def receita_mensal(t: Tables) -> pl.DataFrame:
    """Série financeira mensal — delega a `monthly_churn` de propósito.

    A taxa canônica do projeto tem numerador e denominador da mesma coorte
    (encerradas no mês ÷ ativas no 1º dia). Recalcular aqui produziria um
    segundo número para "churn de dezembro" — 6,75% em vez de 3,52% — e um
    painel que discorda do relatório vale menos que nenhum painel.
    """
    return monthly_churn(exposure_panel(t.subscriptions)).select(
        "month",
        "active_mrr",
        "churned_mrr",
        "mrr_ended_all",
        "churned_subs",
        "ended_all",
        mrr_churn_pct=(100 * pl.col("mrr_churn_rate")).round(2),
        sub_churn_pct=(100 * pl.col("sub_churn_rate")).round(2),
    )


def carga_de_suporte(t: Tables) -> pl.DataFrame:
    """Tickets por prioridade: volume, tempo de resposta e satisfação."""
    return (
        t.support_tickets.group_by("priority")
        .agg(
            tickets=pl.len(),
            resolucao_mediana_h=pl.col("resolution_time_hours").median().round(1),
            primeira_resposta_mediana_min=pl.col("first_response_time_minutes")
            .median()
            .round(0),
            escalacao_pct=(100 * pl.col("escalation_flag").mean()).round(1),
            csat_medio=pl.col("satisfaction_score").mean().round(2),
            sem_csat_pct=(100 * pl.col("satisfaction_score").is_null().mean()).round(1),
        )
        .sort("tickets", descending=True)
    )


def features_com_erro(t: Tables, top_n: int = 10) -> pl.DataFrame:
    """Funcionalidades por taxa de erro — a fila de correção da engenharia."""
    return (
        t.feature_usage.group_by("feature_name")
        .agg(
            usos=pl.col("usage_count").sum(),
            erros=pl.col("error_count").sum(),
            eventos=pl.len(),
            beta=pl.col("is_beta_feature").mean().round(2),
        )
        .with_columns(
            erros_por_100_usos=(100 * pl.col("erros") / pl.col("usos")).round(2)
        )
        .sort("erros_por_100_usos", descending=True)
        .head(top_n)
    )


def motivos_declarados(t: Tables) -> pl.DataFrame:
    """Distribuição dos motivos de churn declarados."""
    total = t.churn_events.height
    return (
        t.churn_events.group_by("reason_code")
        .agg(eventos=pl.len())
        .with_columns(share_pct=(100 * pl.col("eventos") / total).round(1))
        .sort("eventos", descending=True)
    )


# ------------------------------------------------------------------- painéis
def _rows(df: pl.DataFrame) -> list[dict[str, Any]]:
    return json.loads(df.write_json())


def _painel_ceo(t: Tables, r: dict[str, Any], tb: dict[str, pl.DataFrame]) -> dict:
    return {
        "titulo": "Saúde do negócio e preservação de receita",
        "publico": "CEO e comitê executivo",
        "pergunta": "A empresa está perdendo receita mais rápido do que ganha?",
        "kpis": [
            _kpi(
                "Churn de MRR (dez/24)",
                r["mrr_churn_dec24_pct"],
                unidade="%",
                nota=f"contra {r['mrr_churn_ref_avg_pct']}% na média jan–set",
                direcao="ruim",
                chave="mrr_churn_dec24_pct",
            ),
            _kpi(
                "MRR pago ativo",
                r["paid_mrr_active_k"],
                unidade="US$ mil",
                nota="snapshot de 31/12/2024",
                chave="paid_mrr_active_k",
            ),
            _kpi(
                "MRR em risco (90 dias)",
                r["expected_loss_90d_k"],
                unidade="US$ mil",
                nota=f"{r['expected_loss_90d_pct']}% da base ativa",
                direcao="ruim",
                chave="expected_loss_90d_k",
            ),
            _kpi(
                "Excesso sobre o esperado (4º tri)",
                r["q4_ratio_x"],
                unidade="×",
                nota=f"{r['q4_mrr_ratio_x']}× quando medido em MRR",
                direcao="ruim",
                chave="q4_ratio_x",
            ),
        ],
        "descritivo": {
            "titulo": "O churn subiu em taxa, não só em contagem",
            "grafico": "serie_mrr",
            "dados": _rows(receita_mensal(t)),
            "limite_controle": round(
                100 * float(tb["control_chart_2024"]["ucl"][0]), 2
            ),
            "leitura": (
                f"{r['control_breaks']} meses acima do limite de controle. "
                "A base cresceu, mas a taxa subiu junto — não é efeito de tamanho."
            ),
        },
        "diagnostico": {
            "titulo": "A alta está nas assinaturas novas, e só depois da quebra",
            "grafico": "risco_por_idade",
            "dados": _rows(
                tb["hazard_by_age"]
                .select("age_bucket", "period", "hazard")
                .with_columns(hazard_pct=(100 * pl.col("hazard")).round(2))
            ),
            "quebra": {
                "antes": r["hr_before_break_x"],
                "depois": r["hr_after_break_x"],
                "ic_depois": [r["hr_after_ci_low"], r["hr_after_ci_high"]],
            },
            "leitura": (
                f"Risco de {r['hz_0_30_target_pct']}%/mês nos primeiros 30 dias contra "
                f"{r['hz_mature_target_pct']}% nas maduras. A razão passou de "
                f"{r['hr_before_break_x']}× para {r['hr_after_break_x']}× entre set e out/2024."
            ),
        },
        "preditivo": {
            "titulo": "Quanto sai nos próximos 90 dias",
            "grafico": "perda_por_plano",
            "dados": _rows(
                tb["cs_priority_accounts"]
                .group_by("plan_tier")
                .agg(
                    contas=pl.len(),
                    perda_esperada=pl.col("expected_loss_90d").sum().round(0),
                    mrr_ativo=pl.col("active_paid_mrr").sum().round(0),
                )
                .sort("perda_esperada", descending=True)
            ),
            "leitura": (
                f"{r['cs_top_n']} contas concentram US$ {r['cs_top_expected_loss_k']} mil "
                f"({r['cs_top_share_of_loss_pct']}% da perda esperada total)."
            ),
            "confiabilidade": (
                f"Projeção por idade da assinatura (ROC fora do tempo {r['oot_age_roc']}). "
                f"O modelo com as 5 tabelas empata com o acaso ({r['oot_gbm_roc']})."
            ),
        },
        "prescritivo": {
            "titulo": "O que a decisão executiva compra",
            "grafico": "cenarios",
            "dados": [
                {"cenario": "Recuperar 25%", "mrr_mes": r["recovery_25_mrr_month_k"]},
                {"cenario": "Recuperar 50%", "mrr_mes": r["recovery_50_mrr_month_k"]},
                {"cenario": "Recuperar 75%", "mrr_mes": r["recovery_75_mrr_month_k"]},
            ],
            "leitura": (
                "Quanto de MRR mensal volta em cada cenário de recuperação do "
                "excedente da quebra. As três ações abaixo estão ordenadas pela "
                "força da evidência que as sustenta, não pelo tamanho do prêmio."
            ),
            "acoes": [
                {
                    "acao": "Aprovar o experimento de onboarding",
                    "porque": (
                        f"É o único caminho para provar causa: {r['ab_n_per_arm']} assinaturas "
                        f"por braço, {r['ab_weeks_to_enroll']} semanas de recrutamento."
                    ),
                    "confianca": "alta",
                },
                {
                    "acao": "Instituir um log de eventos de negócio",
                    "porque": (
                        f"A quebra custou US$ {r['excess_mrr_q4_k']} mil no 4º tri e nenhuma "
                        "tabela registra preço, release ou campanha para explicá-la."
                    ),
                    "confianca": "alta",
                },
                {
                    "acao": "NÃO financiar migração para plano anual como retenção",
                    "porque": (
                        f"Efeito causal estimado {r['dml_cobranca_anual_theta']} p.p., IC "
                        f"[{r['dml_cobranca_anual_ci_low']}; {r['dml_cobranca_anual_ci_high']}] — "
                        "indistinguível de zero."
                    ),
                    "confianca": "media",
                },
            ],
        },
        "lacunas": [
            _lacuna(
                "Causa da quebra de set–out/2024",
                "Nenhuma das 5 tabelas registra preço, release, campanha ou concorrente.",
            ),
            _lacuna(
                "NRR / expansão de receita",
                "Upgrade e downgrade são flags sem data; não dá para atribuí-los a um mês.",
            ),
        ],
    }


def _painel_vendas(t: Tables, r: dict[str, Any], tb: dict[str, pl.DataFrame]) -> dict:
    return {
        "titulo": "Receita, contratos e verticais",
        "publico": "Liderança comercial",
        "pergunta": "Onde a receita nasce e onde ela vaza?",
        "kpis": [
            _kpi(
                "MRR pago ativo",
                r["paid_mrr_active_k"],
                unidade="US$ mil",
                chave="paid_mrr_active_k",
            ),
            _kpi(
                "Assinaturas ativas",
                r["active_subs_dec24"],
                unidade="",
                nota=f"{r['active_subs_growth_x']}× o início do ano",
                direcao="bom",
                chave="active_subs_dec24",
            ),
            _kpi(
                "MRR perdido no 4º tri",
                r["q4_mrr_lost_k"],
                unidade="US$ mil",
                nota=f"esperado era US$ {r['q4_mrr_expected_k']} mil",
                direcao="ruim",
                chave="q4_mrr_lost_k",
            ),
            _kpi(
                "Saídas no 4º tri",
                r["q4_observed_ended"],
                unidade="",
                nota=f"{r['young_share_q4_events_pct']}% com menos de 90 dias",
                direcao="ruim",
                chave="q4_observed_ended",
            ),
        ],
        "descritivo": {
            "titulo": "MRR ativo por plano",
            "grafico": "mrr_plano",
            "dados": _rows(mrr_por_plano(t)),
            "leitura": "Enterprise carrega o ticket; Basic carrega o volume.",
        },
        "diagnostico": {
            "titulo": "Onde o MRR perdido se concentra",
            "grafico": "saidas_industria",
            "dados": _rows(saidas_por_dimensao(t, "industry")),
            "leitura": (
                "Nenhuma vertical se separa depois da correção de Holm "
                f"(menor p ajustado {r['segments_min_p_holm']}). A diferença é de tamanho de base, "
                "não de propensão a sair."
            ),
        },
        "preditivo": {
            "titulo": "Perda esperada por vertical (90 dias)",
            "grafico": "risco_industria",
            "dados": _rows(
                tb["cs_priority_accounts"]
                .group_by("industry")
                .agg(
                    contas=pl.len(),
                    perda_esperada=pl.col("expected_loss_90d").sum().round(0),
                    assinaturas_novas=pl.col("young_subs").sum(),
                )
                .sort("perda_esperada", descending=True)
            ),
            "leitura": "Ordenado por dinheiro em risco, não por número de contas.",
        },
        "prescritivo": {
            "titulo": "O que mudar no processo comercial",
            "leitura": (
                "Três mudanças de processo, ordenadas por quanto a evidência as sustenta."
            ),
            "grafico": "acoes",
            "dados": [],
            "acoes": [
                {
                    "acao": "Tratar os primeiros 90 dias como parte da venda",
                    "porque": (
                        f"O risco nos primeiros 30 dias é {r['hz_0_30_mult_x']}× o das assinaturas "
                        "maduras, em qualquer vertical."
                    ),
                    "confianca": "alta",
                },
                {
                    "acao": "Não prometer retenção via contrato anual",
                    "porque": "O efeito causal medido é indistinguível de zero.",
                    "confianca": "media",
                },
                {
                    "acao": "Priorizar a fila por MRR, não por contagem",
                    "porque": (
                        f"Em contagem o 4º tri foi {r['q4_ratio_x']}× o esperado; em MRR, "
                        f"{r['q4_mrr_ratio_x']}×. Quem saiu valia mais que a média."
                    ),
                    "confianca": "alta",
                },
            ],
        },
        "lacunas": [
            _lacuna(
                "Pipeline, taxa de conversão e ciclo de venda",
                "Não existe tabela de oportunidades — só assinaturas já fechadas.",
            ),
            _lacuna(
                "Churn pós-upgrade datado",
                "`upgrade_flag` e `downgrade_flag` não têm data: não dá para saber"
                " se o upgrade veio antes da saída.",
            ),
        ],
    }


def _painel_marketing(
    t: Tables, r: dict[str, Any], tb: dict[str, pl.DataFrame]
) -> dict:
    canais = base_por_canal(t)
    return {
        "titulo": "Aquisição por canal e qualidade da base",
        "publico": "Marketing",
        "pergunta": "Que canal traz cliente que fica?",
        "kpis": [
            _kpi(
                "Canais de aquisição",
                canais.height,
                unidade="",
                nota="organic, ads, partner, event, other",
            ),
            _kpi("Contas na base", r["n_accounts"], unidade="", chave="n_accounts"),
            _kpi(
                "Churn precoce (≤90 dias)",
                r["young_share_q4_events_pct"],
                unidade="%",
                nota="das saídas do 4º tri",
                direcao="ruim",
                chave="young_share_q4_events_pct",
            ),
            _kpi(
                "Diferença entre canais",
                0.0,
                unidade="",
                nota="nenhum canal se separa após correção de Holm",
                direcao="neutro",
            ),
        ],
        "descritivo": {
            "titulo": "Base e receita por canal",
            "grafico": "canais",
            "dados": _rows(canais),
            "leitura": "Volume e MRR por origem declarada da conta.",
        },
        "diagnostico": {
            "titulo": "Churn precoce por canal",
            "grafico": "precoce_canal",
            "dados": _rows(
                canais.select("referral_source", "churn_pct", "precoce_pct", "saidas")
            ),
            "leitura": (
                "As diferenças entre canais não sobrevivem à correção para comparações "
                f"múltiplas (menor p ajustado {r['segments_min_p_holm']}). "
                "O canal não prevê quem fica."
            ),
        },
        "preditivo": {
            "titulo": "MRR em risco por canal",
            "grafico": "risco_canal",
            "dados": _rows(
                tb["cs_priority_accounts"]
                .join(
                    t.accounts.select("account_id", "referral_source"),
                    on="account_id",
                    how="left",
                )
                .group_by("referral_source")
                .agg(
                    contas=pl.len(),
                    perda_esperada=pl.col("expected_loss_90d").sum().round(0),
                )
                .sort("perda_esperada", descending=True)
            ),
            "leitura": "Projeção herdada da idade da assinatura, não do canal.",
        },
        "prescritivo": {
            "titulo": "Onde realocar — e onde não realocar",
            "leitura": (
                "Duas decisões: uma de contenção, uma de instrumentação. Nenhuma depende "
                "de um modelo preditivo que não funciona."
            ),
            "grafico": "acoes",
            "dados": [],
            "acoes": [
                {
                    "acao": "Não realocar verba por diferença de churn entre canais",
                    "porque": "A diferença observada está dentro do ruído amostral.",
                    "confianca": "alta",
                },
                {
                    "acao": "Instrumentar custo por canal antes do próximo ciclo",
                    "porque": "Sem custo não existe CAC, ROI nem payback — só volume.",
                    "confianca": "alta",
                },
            ],
        },
        "lacunas": [
            _lacuna(
                "CAC, ROI e verba de mídia",
                "Não há tabela de custo de aquisição nem de investimento por campanha.",
            ),
            _lacuna(
                "LTV",
                "Sem margem e sem custo de serviço, só dá para calcular receita"
                " observada — não valor.",
            ),
            _lacuna(
                "Campanha e oferta promocional",
                "Não existe identificador de campanha nem de desconto de entrada.",
            ),
        ],
    }


def _painel_financeiro(
    t: Tables, r: dict[str, Any], tb: dict[str, pl.DataFrame]
) -> dict:
    reembolsos = reembolsos_por_motivo(t)
    total_reembolso = float(reembolsos["reembolso_total"].sum())
    return {
        "titulo": "Risco financeiro e fluxo recorrente",
        "publico": "Financeiro",
        "pergunta": "Quanto da receita recorrente está em risco, e quanto já virou perda?",
        "kpis": [
            _kpi(
                "MRR pago ativo",
                r["paid_mrr_active_k"],
                unidade="US$ mil",
                chave="paid_mrr_active_k",
            ),
            _kpi(
                "MRR excedente perdido (4º tri)",
                r["excess_mrr_q4_k"],
                unidade="US$ mil",
                nota=f"US$ {r['excess_mrr_per_month_k']} mil/mês",
                direcao="ruim",
                chave="excess_mrr_q4_k",
            ),
            _kpi(
                "Reembolsos emitidos",
                round(total_reembolso),
                unidade="US$",
                nota="acumulado em 600 eventos de churn",
            ),
            _kpi(
                "ARR equivalente a recuperar 50%",
                r["recovery_50_arr_equiv_k"],
                unidade="US$ mil",
                direcao="bom",
                chave="recovery_50_arr_equiv_k",
            ),
        ],
        "descritivo": {
            "titulo": "MRR ativo e MRR perdido, mês a mês",
            "grafico": "serie_financeira",
            "dados": _rows(receita_mensal(t)),
            "leitura": (
                "A receita cresce e a perda cresce mais rápido: o MRR perdido em dezembro é "
                f"{r['mrr_churn_dec24_pct']}% da base contra "
                f"{r['mrr_churn_ref_avg_pct']}% na média do ano."
            ),
        },
        "diagnostico": {
            "titulo": "Reembolso por motivo declarado",
            "grafico": "reembolsos",
            "dados": _rows(reembolsos),
            "leitura": (
                f"US$ {_br(total_reembolso)} no total — ordem de grandeza irrelevante perto de "
                f"US$ {_br(r['excess_mrr_q4_k'])} mil de MRR perdido. O problema não é reembolso."
            ),
        },
        "preditivo": {
            "titulo": "Fluxo recorrente sob cenários de retenção",
            "grafico": "cenarios",
            "dados": [
                {"cenario": "Sem ação", "mrr_mes": 0.0},
                {"cenario": "Recuperar 25%", "mrr_mes": r["recovery_25_mrr_month_k"]},
                {"cenario": "Recuperar 50%", "mrr_mes": r["recovery_50_mrr_month_k"]},
                {"cenario": "Recuperar 75%", "mrr_mes": r["recovery_75_mrr_month_k"]},
            ],
            "leitura": (
                "Cada 25 pontos de recuperação valem cerca de "
                f"US$ {_br(r['recovery_25_mrr_month_k'])} mil/mês "
                "de MRR preservado."
            ),
        },
        "prescritivo": {
            "titulo": "Política financeira",
            "leitura": (
                "Política financeira derivada do tamanho real de cada perda, não da "
                "frequência com que ela aparece."
            ),
            "grafico": "acoes",
            "dados": [],
            "acoes": [
                {
                    "acao": (
                        "Reservar orçamento de win-back proporcional a "
                        f"US$ {_br(r['excess_mrr_per_month_k'])} mil/mês"
                    ),
                    "porque": (
                        "É o excedente mensal atribuível à quebra, "
                        "não ao crescimento da base."
                    ),
                    "confianca": "media",
                },
                {
                    "acao": "Não endurecer política de reembolso",
                    "porque": (
                        f"Reembolsos somam US$ {_br(total_reembolso)} — "
                        "não movem o resultado."
                    ),
                    "confianca": "alta",
                },
            ],
        },
        "lacunas": [
            _lacuna(
                "Margem, custo de serviço e fluxo de caixa",
                "Não há tabela de custos; só receita recorrente contratada.",
            ),
            _lacuna(
                "Descontos e cobrança efetiva",
                "O MRR contratado não diz o que foi faturado nem o que foi pago.",
            ),
        ],
    }


def _painel_operacoes(
    t: Tables, r: dict[str, Any], tb: dict[str, pl.DataFrame]
) -> dict:
    suporte = carga_de_suporte(t)
    return {
        "titulo": "Engajamento do produto e carga de suporte",
        "publico": "Operações e Customer Success",
        "pergunta": "Onde o cliente trava, e a fila do CS está na ordem certa?",
        "kpis": [
            _kpi("Tickets no período", r["n_tickets"], unidade="", chave="n_tickets"),
            _kpi(
                "Tickets sem nota de satisfação",
                r["csat_missing_pct"],
                unidade="%",
                direcao="ruim",
                chave="csat_missing_pct",
            ),
            _kpi(
                "CSAT médio", r["csat_mean_2024"], unidade="/5", chave="csat_mean_2024"
            ),
            _kpi(
                "Uso por assinatura",
                r["usage_change_per_sub_pct"],
                unidade="%",
                nota="variação no ano, com a base crescendo 5,8×",
                direcao="ruim",
                chave="usage_change_per_sub_pct",
            ),
        ],
        "descritivo": {
            "titulo": "Carga de suporte por prioridade",
            "grafico": "suporte",
            "dados": _rows(suporte),
            "leitura": (
                "Tempo de resolução e primeira resposta praticamente idênticos entre "
                "prioridades — a fila não está sendo priorizada."
            ),
            "confiabilidade": AVISO_TICKETS,
        },
        "diagnostico": {
            "titulo": "Funcionalidades por taxa de erro",
            "grafico": "erros_feature",
            "dados": _rows(features_com_erro(t)),
            "leitura": (
                "As taxas de erro ficam todas entre 6,0 e 6,6 por 100 usos: distribuição "
                "uniforme, não um gargalo. E erro não separa quem sai "
                f"(AUC {r['rate_errors_auc_all']})."
            ),
            "confiabilidade": AVISO_USO,
        },
        "preditivo": {
            "titulo": "Motivos declarados de saída",
            "grafico": "motivos",
            "dados": _rows(motivos_declarados(t)),
            "leitura": (
                f"Distribuição quase uniforme, de {r['reason_share_min_pct']}% a "
                f"{r['reason_share_max_pct']}% — e o motivo declarado quase não se relaciona com a "
                f"categoria do ticket (V de Cramér {r['reason_feedback_cramers_v']})."
            ),
        },
        "prescritivo": {
            "titulo": "A fila do CS",
            "grafico": "fila_cs",
            "dados": _rows(
                tb["cs_priority_accounts"]
                .head(15)
                .select(
                    "account_id",
                    "account_name",
                    "industry",
                    "plan_tier",
                    "active_paid_mrr",
                    "young_subs",
                    "expected_loss_90d",
                    "motivo",
                    "acao_sugerida",
                )
            ),
            "leitura": (
                f"{r['cs_top_n']} contas, ordenadas por risco × MRR. As 15 primeiras aparecem "
                "aqui; a lista completa sai em CSV a cada execução."
            ),
            "acoes": [
                {
                    "acao": (
                        "Contato marcado em D+7 e D+21 para assinatura nova "
                        "acima do corte de MRR"
                    ),
                    "porque": f"Risco de {r['hz_0_30_target_pct']}%/mês nos primeiros 30 dias.",
                    "confianca": "alta",
                },
                {
                    "acao": "Parar de usar CSAT como gatilho de risco",
                    "porque": (
                        f"AUC {r['csat_auc']} — não separa quem sai, e falta "
                        f"em {r['csat_missing_pct']}% dos tickets."
                    ),
                    "confianca": "alta",
                },
            ],
        },
        "lacunas": [
            _lacuna(
                "Frequência de login e sessões",
                "Não existe tabela de sessão — só eventos de uso de funcionalidade.",
            ),
            _lacuna(
                "Adoção de funcionalidade de IA",
                "As funcionalidades são anônimas (`feature_1`…`feature_40`);"
                " não dá para isolar as de IA.",
            ),
            _lacuna(
                "Health score longitudinal",
                "Depende de série de uso confiável, e 76,6% dos eventos têm data ruim.",
            ),
        ],
    }


CONSTRUTORES = {
    "ceo": _painel_ceo,
    "vendas": _painel_vendas,
    "marketing": _painel_marketing,
    "financeiro": _painel_financeiro,
    "operacoes": _painel_operacoes,
}


def build_payload(
    t: Tables, report: dict[str, Any], tables: dict[str, pl.DataFrame]
) -> dict[str, Any]:
    """Monta o JSON completo dos cinco painéis."""
    return {
        "gerado_por": "churn_diag.dashboards",
        "snapshot": str(SNAPSHOT_DATE),
        "inicio_periodo_alvo": str(TARGET_START),
        "aviso": (
            "Todo número vem de outputs/metrics.json ou das 5 tabelas do dataset. "
            "KPIs que o dataset não sustenta aparecem na seção 'lacunas' de cada painel, "
            "em branco — nunca preenchidos com estimativa."
        ),
        "paineis": {
            nome: CONSTRUTORES[nome](t, report, tables) for nome in STAKEHOLDERS
        },
    }


def write_payload(payload: dict[str, Any], path: Path) -> Path:
    """Grava `dashboard/data.js` — atribuição global, para abrir via file://."""
    path.parent.mkdir(parents=True, exist_ok=True)
    corpo = json.dumps(
        payload, indent=2, ensure_ascii=False, sort_keys=True, default=str
    )
    path.write_text(f"window.DASHBOARD_DATA = {corpo};\n", encoding="utf-8")
    return path
