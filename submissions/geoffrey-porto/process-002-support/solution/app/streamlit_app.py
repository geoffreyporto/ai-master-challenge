"""Redesign de Suporte — app do Diretor de Operações (Challenge 002).

Rodar: `uv run python -m support_redesign` (uma vez) e
`uv run streamlit run app/streamlit_app.py`.
"""

from __future__ import annotations

import copy
import json
import os
import pickle
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import numpy as np
import plotly.express as px
import polars as pl
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from support_redesign import roi  # noqa: E402
from support_redesign.bootstrap import ensure_artifacts  # noqa: E402
from support_redesign.boundary import decide  # noqa: E402
from support_redesign.config import (  # noqa: E402
    ASSUMPTIONS_FILE,
    MAX_TEXT_CHARS,
    MODEL2VEC_NAME,
    OUTPUTS_DIR,
    SEED,
    resolve_data_dir,
)
from support_redesign.diagnosis import CSAT, closed_with_hours  # noqa: E402
from support_redesign.drafting import draft_reply  # noqa: E402
from support_redesign.io import load_d1  # noqa: E402
from support_redesign.pioneer import PioneerClient, PioneerKeyMissingError  # noqa: E402
from support_redesign.router_bin import ensure_running  # noqa: E402

ROUTER_ADDR = os.environ.get("ROUTER_ADDR", "127.0.0.1:8080")
ROUTER_URL = f"http://{ROUTER_ADDR}/route"
PUBLIC_DEMO = os.environ.get("SUPPORT_PUBLIC_DEMO") == "1"
MODELS = OUTPUTS_DIR / "models"

st.set_page_config(page_title="Redesign de Suporte", layout="wide")


@st.cache_resource(show_spinner=False)
def bootstrap() -> bool:
    return ensure_artifacts()


with st.spinner(
    "Primeira execução: treinando os modelos e medindo o hold-out (~1 min)…"
):
    bootstrap()


@st.cache_data
def load_metrics() -> dict[str, Any]:
    return json.loads((OUTPUTS_DIR / "metrics.json").read_text())


@st.cache_resource
def load_production() -> dict[str, Any]:
    with (MODELS / "b0.pkl").open("rb") as fh:
        return pickle.load(fh)  # noqa: S301 — artefato local gerado pelo pipeline


@st.cache_resource
def load_index() -> tuple[Any, np.ndarray, pl.DataFrame]:
    from model2vec import StaticModel

    encoder = StaticModel.from_pretrained(MODEL2VEC_NAME)
    return (
        encoder,
        np.load(MODELS / "index_embeddings.npy"),
        pl.read_parquet(MODELS / "index_rows.parquet"),
    )


@st.cache_data
def load_tables() -> tuple[pl.DataFrame, pl.DataFrame, pl.DataFrame]:
    d1 = closed_with_hours(load_d1(resolve_data_dir()))
    return (
        d1,
        pl.read_parquet(OUTPUTS_DIR / "d2_test.parquet"),
        pl.read_parquet(OUTPUTS_DIR / "d1_scored.parquet"),
    )


def similar(text: str, k: int = 5) -> pl.DataFrame:
    from support_redesign.text import normalize

    encoder, matrix, rows = load_index()
    q = encoder.encode([normalize(text)])[0]
    q = q / max(float(np.linalg.norm(q)), 1e-12)
    sims = matrix @ q.astype(np.float32)
    top = np.argsort(-sims)[:k]
    return rows[top.tolist()].with_columns(
        pl.Series("similaridade", sims[top].round(3))
    )


def call_rust(text: str, priority: str | None) -> dict[str, Any] | None:
    body = json.dumps({"text": text, "priority": priority}).encode()
    req = urllib.request.Request(
        ROUTER_URL, data=body, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=0.5) as resp:  # noqa: S310 — URL local configurável
            return json.loads(resp.read())
    except urllib.error.URLError, TimeoutError, ValueError:
        return None


@st.cache_resource
def router_status() -> tuple[bool, str]:
    return ensure_running(ROUTER_ADDR)


m = load_metrics()
rep = m["report"]
d1, d2_test, d1_scored = load_tables()

st.title("Redesign de Suporte — onde perdemos tempo, o que automatizar, e rodando")
c = st.columns(4)
c[0].metric(
    "Macro-F1 no hold-out",
    rep["b0_macro_f1"],
    help=f"{rep['test_n']} tickets nunca vistos",
)
c[1].metric("Roteamento automático", rep["coverage_auto"], help="fração do hold-out")
c[2].metric("Precisão dos automáticos", rep["precision_auto"])
c[3].metric("Horas líquidas/mês (base)", rep["roi_net_hours_base"])

router_up, router_msg = router_status()
st.caption(
    ("Roteador Rust no ar: " if router_up else "Roteador Rust fora do ar: ")
    + router_msg
)

tabs = st.tabs(["Diagnóstico", "Roteador", "Fronteira IA × humano", "Similares", "ROI"])

with tabs[0]:
    audit = m["audit"]
    st.subheader("Os dados são confiáveis?")
    st.table(
        pl.DataFrame(
            {
                "Dataset": ["1 — métricas operacionais", "2 — tickets de TI"],
                "Veredito": [audit["d1"]["verdict"], audit["d2"]["verdict"]],
                "Linhas": [
                    audit["d1"]["evidence"]["rows"],
                    audit["d2"]["evidence"]["rows"],
                ],
            }
        )
    )
    st.warning(
        f"Dataset 1 é sintético: `{{product_purchased}}` em {rep['d1_placeholder_share']} das "
        f"descrições e {rep['d1_negative_share']} dos fechados 'resolvidos antes da 1ª resposta'. "
        "Os gráficos abaixo mostram o pipeline funcionando — não um gargalo real."
    )
    f = st.columns(3)
    channels = f[0].multiselect("Canal", sorted(d1["Ticket Channel"].unique()))
    priorities = f[1].multiselect("Prioridade", sorted(d1["Ticket Priority"].unique()))
    types = f[2].multiselect("Tipo", sorted(d1["Ticket Type"].unique()))
    view = d1
    for col, sel in (
        ("Ticket Channel", channels),
        ("Ticket Priority", priorities),
        ("Ticket Type", types),
    ):
        if sel:
            view = view.filter(pl.col(col).is_in(sel))
    st.caption(f"{view.height} tickets fechados no filtro")
    if view.height:
        heat = view.group_by("Ticket Channel", "Ticket Priority").agg(
            pl.col("hours").median().alias("mediana_horas"),
            pl.col(CSAT).mean().alias("csat"),
        )
        g = st.columns(2)
        g[0].plotly_chart(
            px.density_heatmap(
                heat,
                x="Ticket Priority",
                y="Ticket Channel",
                z="mediana_horas",
                histfunc="avg",
                title="Mediana resposta→resolução (h)",
            ),
            width="stretch",
        )
        g[1].plotly_chart(
            px.density_heatmap(
                heat,
                x="Ticket Priority",
                y="Ticket Channel",
                z="csat",
                histfunc="avg",
                title="CSAT médio",
            ),
            width="stretch",
        )
    tests = [
        {
            "teste": k.replace("|", " × "),
            "p": round(v["p"], 3),
            "ε²": round(v["epsilon2"], 4),
        }
        for k, v in m["diagnosis"]["tests"].items()
    ]
    st.dataframe(pl.DataFrame(tests), hide_index=True)
    st.info(
        f"Menor diferença de CSAT detectável entre canais: {rep['csat_mde']} ponto; "
        f"a maior observada é {rep['csat_max_diff']}. Pseudo-R² do modelo ordinal: "
        f"{rep['csat_pseudo_r2']}. Sem driver detectável."
    )
    st.dataframe(pl.DataFrame(m["diagnosis"]["findings"]), hide_index=True)

with tabs[1]:
    prod = load_production()
    clf, policy = prod["clf"], prod["policy"]
    st.subheader("Um ticket entra: o que acontece?")
    if "pick" not in st.session_state:
        st.session_state.pick = None
        st.session_state.rng = np.random.default_rng(SEED)
        st.session_state.texto = ""
    if st.button("Sortear ticket do hold-out", key="sortear"):
        st.session_state.pick = int(st.session_state.rng.integers(d2_test.height))
        st.session_state.texto = d2_test["Document"][st.session_state.pick]
    default = (
        d2_test["Document"][st.session_state.pick]
        if st.session_state.pick is not None
        else ""
    )
    text = st.text_area("Texto do ticket", max_chars=MAX_TEXT_CHARS, key="texto")
    priority = st.selectbox(
        "Prioridade informada", ["(nenhuma)", "Low", "Medium", "High", "Critical"]
    )
    prio = None if priority == "(nenhuma)" else priority
    if text.strip():
        proba = clf.predict_proba([text])[0]
        d = decide(policy, proba, prio, float(clf.known_share([text])[0]))
        cols = st.columns(4)
        cols[0].metric("Fila prevista", d.topic)
        cols[1].metric("Confiança", f"{d.confidence:.3f}")
        cols[2].metric("Ação", d.action.upper())
        if st.session_state.pick is not None and text == default:
            truth = d2_test["Topic_group"][st.session_state.pick]
            cols[3].metric(
                "Fila verdadeira",
                truth,
                delta="acertou" if truth == d.topic else "errou",
            )
        st.write(f"**Motivo:** {d.reason}")
        st.caption(f"Conjunto conformal: {', '.join(d.prediction_set) or '(vazio)'}")
        st.bar_chart(
            pl.DataFrame({"fila": list(clf.classes_), "probabilidade": proba}),
            x="fila",
            y="probabilidade",
        )
        rust = call_rust(text, prio)
        if rust:
            same = rust["topic"] == d.topic and rust["action"] == d.action
            st.success(
                f"Roteador Rust ({ROUTER_URL}): {rust['topic']} / {rust['action']} — "
                + ("mesma decisão" if same else "DIVERGE")
            )
        else:
            st.caption(f"Roteador Rust offline — {router_status()[1]}")
        st.write("**Tickets parecidos já tratados**")
        sim = similar(text)
        st.dataframe(sim, hide_index=True)
        st.write(
            "**Rascunho de resposta (Pioneer: máscara → DeepSeek-V4-Flash → guardrail)**"
        )
        if PUBLIC_DEMO:
            st.info(
                "Rascunho desligado na versão pública: ele usa a chave do Pioneer do "
                "autor. Rode o app localmente com a sua chave para testar."
            )
        elif st.button("Gerar rascunho", key="rascunho"):
            try:
                client = PioneerClient()
            except PioneerKeyMissingError:
                st.info(
                    "Sem chave do Pioneer: defina PIONEER_API_KEY, PIONEER_ENV_FILE "
                    "ou crie solution/.env com PIONEER_API_KEY=..."
                )
            else:
                try:
                    dr = draft_reply(
                        client, text, d.topic, sim["Document"].head(3).to_list()
                    )
                finally:
                    client.close()
                st.caption(f"Enviado ao LLM (mascarado): {dr.masked_input[:300]}")
                st.text_area(
                    "Rascunho — requer aprovação do agente", dr.text, disabled=True
                )
                if dr.guardrail_ok:
                    st.success("Guardrail de PII: aprovado")
                else:
                    st.error(f"Guardrail de PII: bloqueado {dr.guardrail_entities}")
    st.caption(
        f"Métricas do topo: hold-out inteiro ({rep['test_n']} tickets), não os exemplos desta tela."
    )

with tabs[2]:
    t = m["boundary"]["test"]
    st.subheader("Onde a IA para e o humano assume")
    cols = st.columns(4)
    cols[0].metric("Automático", rep["coverage_auto"])
    cols[1].metric("Humano", rep["human_share"])
    cols[2].metric("Precisão automática", rep["precision_auto"])
    cols[3].metric("Cobertura conformal", rep["conformal_coverage"])
    rc = pl.DataFrame(m["boundary"]["risk_coverage"])
    st.plotly_chart(
        px.line(
            rc,
            x="coverage",
            y="precision",
            hover_data=["threshold"],
            title="Risco × cobertura (limiar global, hold-out)",
        ),
        width="stretch",
    )
    per_class = [{"fila": k, **v} for k, v in t["per_class"].items()]
    st.dataframe(pl.DataFrame(per_class), hide_index=True)
    st.write("**Tickets reais enviados a humano (sorteados com semente)**")
    st.dataframe(pl.DataFrame(m["boundary"]["human_examples"]), hide_index=True)
    cr = m["cross"]
    st.write(
        f"**Ticket de outro domínio (Dataset 1):** {rep['d1_human_share']} vai para humano "
        f"(vs {rep['human_share']} no Dataset 2); KS p = {cr['ks_p']:.1e}."
    )
    st.dataframe(
        d1_scored.group_by("action").len().sort("len", descending=True), hide_index=True
    )
    h = m.get("hosted")
    if h:
        st.subheader("Modelos hospedados (Pioneer)")
        bench = [
            {
                "modelo": v["model"],
                "amostra": v["n"],
                "macro_f1": round(v["macro_f1"], 3),
                "acurácia": round(v["accuracy"], 3),
            }
            for v in (h["b2_test"], *(h["llm_sample"][k] for k in ("b0", "b2", "llm")))
        ]
        st.dataframe(pl.DataFrame(bench), hide_index=True)
        so = h["second_opinion"]
        st.write(
            f"**Segunda opinião GLiNER2** — precisão na validação "
            f"{rep['so_val_precision']}, no teste {rep['so_test_precision']}; "
            f"regra {'ATIVA' if so['val']['enabled'] else 'desligada (não atingiu a meta)'}."
        )
        st.write(
            f"**Privacidade** — recall da máscara: nomes {rep['pii_name_recall']}, "
            f"e-mails {rep['pii_email_recall']} (n={rep['pii_n']}). "
            f"**Rascunhos** — {rep['draft_leaks']} vazamentos em {rep['draft_n']}; "
            f"guardrail aprovou {rep['draft_guard_pass']}."
        )

with tabs[3]:
    st.subheader("Busca de tickets parecidos (base para respostas sugeridas)")
    r, ch = m["retrieval"]["recall"], m["retrieval"]["chance"]
    st.dataframe(
        pl.DataFrame(
            {"k": list(r), "Recall@k": list(r.values()), "sorteio": list(ch.values())}
        ),
        hide_index=True,
    )
    st.caption(
        "Recall@k mede se algum vizinho é da mesma fila — não a qualidade da resposta: "
        "os datasets não têm resolução real."
    )
    q = st.text_input(
        "Buscar", value="cannot access shared drive permission denied", key="busca"
    )
    if q.strip():
        st.dataframe(similar(q, 10), hide_index=True)

with tabs[4]:
    st.subheader("Quanto economiza — troque as premissas")
    a = roi.load_assumptions(ASSUMPTIONS_FILE)
    s = st.columns(4)
    vol = s[0].number_input(
        "Tickets/ano", value=int(a["tickets_per_year"]["valor"]), step=1000
    )
    tri = s[1].slider(
        "Min. de triagem", 0.5, 10.0, a["triage_minutes_per_ticket"]["valor"]["base"]
    )
    rew = s[2].slider(
        "Min. de retrabalho por erro",
        1.0,
        60.0,
        a["rework_minutes_per_misroute"]["valor"]["base"],
    )
    cost = s[3].slider(
        "R$/hora carregado", 20.0, 200.0, a["loaded_cost_brl_per_hour"]["valor"]["base"]
    )
    custom = copy.deepcopy(a)
    custom["tickets_per_year"]["valor"] = vol
    custom["triage_minutes_per_ticket"]["valor"]["base"] = tri
    custom["rework_minutes_per_misroute"]["valor"]["base"] = rew
    custom["loaded_cost_brl_per_hour"]["valor"]["base"] = cost
    t = m["boundary"]["test"]
    out = roi.scenario(custom, t["coverage_auto"], t["precision_auto"], "base")
    k = st.columns(3)
    k[0].metric(
        "Horas de triagem poupadas/mês", f"{out['triage_hours_saved_month']:.0f}"
    )
    k[1].metric("Horas de retrabalho criadas/mês", f"{out['rework_hours_month']:.1f}")
    k[2].metric(
        "Economia líquida/ano", f"R$ {out['net_brl_year']:,.0f}".replace(",", ".")
    )
    st.dataframe(
        pl.DataFrame([{"faixa": b, **v} for b, v in m["roi"].items()]), hide_index=True
    )
    st.caption(
        "Cobertura e precisão são medidas no hold-out; o resto é premissa (Q-002, Q-003)."
    )
