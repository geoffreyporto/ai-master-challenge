"""Diagnóstico de Churn RavenStack — versão Streamlit.

Não recalcula nada: lê `outputs/metrics.json` e os CSVs que o pipeline
(`uv run python -m churn_diag`) já gravou. O mesmo princípio do resto da
entrega — nenhum número nasce nesta tela — vale aqui também.

Rodar local:
    streamlit run streamlit_app/app.py

No Streamlit Community Cloud, aponte para este arquivo com o repositório
raiz do fork; os `outputs/` já vêm versionados no submodule da submissão,
então não é preciso rodar o pipeline na nuvem.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

RAIZ = Path(__file__).resolve().parents[1]
OUTPUTS = RAIZ / "outputs"

st.set_page_config(
    page_title="RavenStack — Diagnóstico de Churn",
    page_icon="📉",
    layout="wide",
)


@st.cache_data
def carregar_metrics() -> dict:
    caminho = OUTPUTS / "metrics.json"
    if not caminho.exists():
        return {}
    return json.loads(caminho.read_text(encoding="utf-8"))


@st.cache_data
def carregar_csv(nome: str) -> pd.DataFrame:
    caminho = OUTPUTS / f"{nome}.csv"
    if not caminho.exists():
        return pd.DataFrame()
    return pd.read_csv(caminho)


def br(v: float, casas: int = 1) -> str:
    if v is None:
        return "—"
    texto = f"{v:,.{casas}f}"
    return texto.replace(",", "§").replace(".", ",").replace("§", ".")


payload = carregar_metrics()
r = payload.get("report", {})

if not r:
    st.error(
        "`outputs/metrics.json` não encontrado. Rode `uv run python -m churn_diag` "
        "na pasta `solution/` para gerar os outputs antes de abrir este app."
    )
    st.stop()

st.title("📉 RavenStack — Diagnóstico de Churn")
st.caption(
    "Todo número desta tela vem de `outputs/metrics.json` ou dos CSVs do pipeline — "
    "nada é digitado à mão. Relatório completo em `solution/RELATORIO.md`; "
    "painéis interativos por stakeholder em `solution/dashboard/`."
)

col1, col2, col3, col4 = st.columns(4)
col1.metric(
    "Churn de MRR (dez/24)",
    f"{br(r.get('mrr_churn_dec24_pct'))}%",
    delta=f"vs {br(r.get('mrr_churn_ref_avg_pct'))}% jan–set",
    delta_color="inverse",
)
col2.metric("MRR pago ativo", f"{br(r.get('paid_mrr_active_k'), 0)}k", help="MRR pago ativo, US$ milhares")
col3.metric(
    "MRR em risco (90 dias)",
    f"US$ {br(r.get('expected_loss_90d_k'), 0)} mil",
    delta=f"{br(r.get('expected_loss_90d_pct'))}% da base",
    delta_color="inverse",
)
col4.metric(
    "Excesso 4º tri (mix de idade)",
    f"{br(r.get('q4_ratio_x'))}×",
    delta=f"{br(r.get('q4_mrr_ratio_x'))}× em MRR",
    delta_color="inverse",
)

aba_desc, aba_pred, aba_causal, aba_xai, aba_cs, aba_paineis = st.tabs(
    [
        "📊 Descritivo",
        "🔮 Preditivo",
        "🔬 Causal",
        "🔍 Explicabilidade",
        "🎯 Lista do CS",
        "🖥️ Painéis & Arquitetura",
    ]
)

with aba_desc:
    st.subheader("O churn subiu em taxa, não só em contagem")
    monthly = carregar_csv("monthly_churn")
    if not monthly.empty:
        serie = monthly[monthly["month"] >= "2024-01-01"].copy()
        serie["mrr_churn_pct"] = 100 * serie["mrr_churn_rate"]
        st.line_chart(serie, x="month", y="mrr_churn_pct", height=320)
    st.markdown(
        f"- **{br(r.get('control_breaks'), 0)} meses** acima do limite de controle "
        f"({br(r.get('control_ucl_pct'), 2)}%).\n"
        f"- Risco no 1º mês: **{br(r.get('hz_0_30_target_pct'))}%/mês** contra "
        f"**{br(r.get('hz_mature_target_pct'))}%** nas maduras "
        f"({br(r.get('hz_0_30_mult_x'), 1)}× o risco).\n"
        f"- Quebra de regime: razão de risco **{br(r.get('hr_before_break_x'), 1)}×** "
        f"antes de out/2024, **{br(r.get('hr_after_break_x'), 1)}×** depois."
    )
    hazard = carregar_csv("hazard_by_age")
    if not hazard.empty:
        st.caption("Risco mensal por faixa de idade e período")
        st.dataframe(hazard, use_container_width=True, hide_index=True)

with aba_pred:
    st.subheader("O modelo funciona? (honestidade sobre a validação)")
    oot = carregar_csv("oot_validation")
    if not oot.empty:
        st.dataframe(oot, use_container_width=True, hide_index=True)
    st.markdown(
        f"- Só a **idade da assinatura** tem sinal real fora do tempo "
        f"(ROC {br(r.get('oot_age_roc'), 2)}, p={br(r.get('oot_age_p'), 3)}).\n"
        f"- O GBM com as 5 tabelas: **{br(r.get('oot_gbm_insample_roc'), 2)}** no treino "
        f"→ **{br(r.get('oot_gbm_roc'), 2)}** fora do tempo — decorou.\n"
        f"- Ordenar só por MRR captura **{br(r.get('oot_mrr_only_mrr_recall_pct'))}%** "
        f"do MRR que sai no topo da fila; o GBM, **{br(r.get('oot_gbm_mrr_recall_pct'))}%**."
    )

with aba_causal:
    st.subheader("Double Machine Learning — dois casos de uso")
    dml = carregar_csv("dml_use_cases")
    if not dml.empty:
        st.dataframe(dml, use_container_width=True, hide_index=True)
    cate = carregar_csv("cate_quantiles")
    if not cate.empty:
        st.caption("Escada de CATE (cobrança anual), avaliada fora da amostra")
        st.bar_chart(cate, x="quantil", y="efeito_medio", height=280)
        st.markdown(
            f"Amplitude de **{br(r.get('cate_spread_pp'), 2)} p.p.** contra erro-padrão "
            f"de até **{br(r.get('cate_max_se_pp'), 2)} p.p.** — "
            + ("há heterogeneidade aproveitável." if r.get("cate_heterogeneidade") else "escada plana, sem subgrupo a mirar.")
        )

with aba_xai:
    st.subheader("Auditoria por Shapley exato")
    st.markdown(
        f"ROC do modelo de auditoria fora do tempo: **{br(r.get('xai_audit_roc'), 4)}** · "
        f"erro de eficiência: **{r.get('xai_efficiency_error', 0):.1e}** · "
        f"variável mais influente move o risco em **{br(r.get('xai_top_feature_pp'), 2)} p.p.** · "
        f"**{int(r.get('xai_sign_flip_n', 0))} de {int(r.get('xai_features_n', 0))}** variáveis "
        f"trocam de sinal entre indústrias."
    )
    shap_summary = carregar_csv("shapley_summary")
    if not shap_summary.empty:
        st.dataframe(shap_summary, use_container_width=True, hide_index=True)
    figuras = sorted((OUTPUTS / "figures").glob("*.png")) if (OUTPUTS / "figures").exists() else []
    if figuras:
        st.caption("Figuras geradas pelo pipeline (outputs/figures/)")
        cols = st.columns(3)
        for i, fig in enumerate(figuras):
            cols[i % 3].image(str(fig), caption=fig.name, use_container_width=True)

with aba_cs:
    st.subheader(f"Fila priorizada do CS ({int(r.get('cs_top_n', 0))} contas)")
    cs = carregar_csv("cs_priority_accounts")
    if not cs.empty:
        st.dataframe(cs, use_container_width=True, hide_index=True)
        st.download_button(
            "Baixar CSV completo",
            cs.to_csv(index=False).encode("utf-8"),
            file_name="cs_priority_accounts.csv",
            mime="text/csv",
        )

with aba_paineis:
    st.subheader("Painéis por stakeholder e diagrama de arquitetura")
    st.markdown(
        "Estas duas peças são páginas client-side (TypeScript + Chart.js + "
        "Plotly.js e Archify), hospedadas separadamente porque o Streamlit "
        "não serve HTML estático arbitrário com o mesmo controle de assets:\n\n"
        "- **5 painéis de decisão** (CEO, Vendas, Marketing, Financeiro, "
        "Operações/CS) — cada KPI rastreável ao `metrics.json`, lacunas do "
        "dataset declaradas em vez de estimadas.\n"
        "- **Diagrama de arquitetura interativo** — dado → modelagem → entrega, "
        "com views guiadas e tema claro/escuro.\n\n"
        "Links no README da submissão."
    )
    st.info(
        "Para rodar localmente: `python3 -m http.server 8777 --directory "
        "solution/dashboard` e abrir `http://localhost:8777`."
    )

st.divider()
st.caption(
    "Diagnóstico de Churn RavenStack — G4 AI Master Challenge 001 · "
    "Pipeline: Python 3.14 + Polars · Spec-driven (onp-spec), 47 critérios "
    "de aceite provados · Repositório: submissions/geoffrey-porto/"
)
