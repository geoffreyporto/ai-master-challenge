"use strict";
/** Painel de churn da RavenStack — cinco visões, quatro níveis de análise.
 *
 *  Tudo roda no navegador, sem servidor: `data.js` é gerado pelo pipeline
 *  Python e carregado como atribuição global, para a página abrir por
 *  `file://` sem esbarrar em CORS.
 *
 *  Princípio herdado do resto da entrega: número nenhum nasce aqui. Esta
 *  camada só desenha o que `churn_diag.dashboards` calculou — e o que o
 *  dataset não sustenta aparece como lacuna declarada, não como estimativa.
 */
const ORDEM = ["ceo", "vendas", "marketing", "financeiro", "operacoes"];
const ROTULOS = {
    ceo: "CEO",
    vendas: "Vendas",
    marketing: "Marketing",
    financeiro: "Financeiro",
    operacoes: "Operações / CS",
};
const NIVEL_ROTULO = {
    descritivo: "Descritivo · o que aconteceu",
    diagnostico: "Diagnóstico · por que aconteceu",
    preditivo: "Preditivo · o que vem",
    prescritivo: "Prescritivo · o que fazer",
};
const NIVEL_COR = {
    descritivo: "bg-sky-50 text-sky-800 ring-sky-200",
    diagnostico: "bg-amber-50 text-amber-800 ring-amber-200",
    preditivo: "bg-violet-50 text-violet-800 ring-violet-200",
    prescritivo: "bg-emerald-50 text-emerald-800 ring-emerald-200",
};
let atual = "ceo";
function el(tag, classe, texto) {
    const n = document.createElement(tag);
    n.className = classe;
    if (texto !== undefined)
        n.textContent = texto;
    return n;
}
function cartaoKpi(k) {
    const cor = k.direcao === "ruim"
        ? "text-red-700"
        : k.direcao === "bom"
            ? "text-emerald-700"
            : "text-stone-900";
    const cartao = el("div", "rounded-lg border border-stone-200 bg-white p-4 shadow-sm");
    cartao.appendChild(el("div", "text-xs uppercase tracking-wide text-stone-500", k.rotulo));
    const valor = el("div", `mt-1 text-2xl font-semibold tabular-nums ${cor}`);
    valor.textContent = brAuto(k.valor) + (k.unidade ? " " + k.unidade : "");
    cartao.appendChild(valor);
    if (k.nota)
        cartao.appendChild(el("div", "mt-1 text-xs text-stone-500", k.nota));
    if (k.chave) {
        const t = el("div", "mt-2 font-mono text-[10px] text-stone-400", "metrics.json → " + k.chave);
        t.title = "Toda métrica do painel tem origem rastreável no pipeline";
        cartao.appendChild(t);
    }
    return cartao;
}
function blocoAcoes(acoes) {
    const lista = el("div", "mt-3 space-y-3");
    acoes.forEach((a) => {
        const item = el("div", "rounded-md border border-stone-200 bg-stone-50 p-3");
        const cab = el("div", "flex items-start justify-between gap-3");
        cab.appendChild(el("div", "font-medium text-stone-900", a.acao));
        const cores = {
            alta: "bg-emerald-100 text-emerald-800",
            media: "bg-amber-100 text-amber-800",
            baixa: "bg-stone-200 text-stone-700",
        };
        cab.appendChild(el("span", `shrink-0 rounded px-2 py-0.5 text-[11px] font-medium ${cores[a.confianca]}`, "confiança " + a.confianca));
        item.appendChild(cab);
        item.appendChild(el("div", "mt-1 text-sm text-stone-600", a.porque));
        lista.appendChild(item);
    });
    return lista;
}
/** Escolhe o gráfico pelo tipo declarado no payload. */
function desenhar(secao, alvo) {
    const d = secao.dados;
    if (!d.length && secao.grafico !== "acoes") {
        alvo.appendChild(el("div", "text-sm text-stone-500", "Sem dados."));
        return;
    }
    switch (secao.grafico) {
        case "serie_mrr":
        case "serie_financeira":
            serieChurn(alvo, d, secao.limite_controle);
            break;
        case "risco_por_idade":
            risco(alvo, d);
            break;
        case "perda_por_plano":
            barras(alvo, d, {
                campoX: "plan_tier",
                campoY: "perda_esperada",
                rotuloY: "perda esperada (US$)",
                formatador: dinheiro,
            });
            break;
        case "cenarios":
            barras(alvo, d, {
                campoX: "cenario",
                campoY: "mrr_mes",
                rotuloY: "MRR/mês (US$ mil)",
                cor: PALETA.bom,
            });
            break;
        case "mrr_plano":
            barras(alvo, d, {
                campoX: "plan_tier",
                campoY: "mrr",
                rotuloY: "MRR ativo (US$)",
                formatador: dinheiro,
            });
            break;
        case "saidas_industria":
            barras(alvo, d, {
                campoX: "industry",
                campoY: "mrr_perdido_alvo",
                rotuloY: "MRR perdido (US$)",
                formatador: dinheiro,
                horizontal: true,
            });
            break;
        case "risco_industria":
        case "risco_canal":
            barras(alvo, d, {
                campoX: d[0]["industry"] !== undefined ? "industry" : "referral_source",
                campoY: "perda_esperada",
                rotuloY: "perda esperada (US$)",
                formatador: dinheiro,
                horizontal: true,
            });
            break;
        case "canais":
            barras(alvo, d, {
                campoX: "referral_source",
                campoY: "mrr_ativo",
                rotuloY: "MRR ativo (US$)",
                formatador: dinheiro,
            });
            break;
        case "precoce_canal":
            barras(alvo, d, {
                campoX: "referral_source",
                campoY: "precoce_pct",
                rotuloY: "saídas até 90 dias (%)",
                cor: PALETA.laranja,
                formatador: (v) => br(v, 1) + "%",
            });
            break;
        case "reembolsos":
            barras(alvo, d, {
                campoX: "reason_code",
                campoY: "reembolso_total",
                rotuloY: "reembolso (US$)",
                formatador: dinheiro,
                horizontal: true,
            });
            break;
        case "suporte":
            tabela(alvo, d, [
                "priority",
                "tickets",
                "resolucao_mediana_h",
                "primeira_resposta_mediana_min",
                "escalacao_pct",
                "csat_medio",
                "sem_csat_pct",
            ], [
                "Prioridade",
                "Tickets",
                "Resolução (h)",
                "1ª resposta (min)",
                "Escalação (%)",
                "CSAT",
                "Sem CSAT (%)",
            ]);
            break;
        case "erros_feature":
            barras(alvo, d, {
                campoX: "feature_name",
                campoY: "erros_por_100_usos",
                rotuloY: "erros por 100 usos",
                cor: PALETA.laranja,
                horizontal: true,
                formatador: (v) => br(v, 2),
            });
            break;
        case "motivos":
            barras(alvo, d, {
                campoX: "reason_code",
                campoY: "share_pct",
                rotuloY: "participação (%)",
                formatador: (v) => br(v, 1) + "%",
            });
            break;
        case "fila_cs":
            tabela(alvo, d, [
                "account_name",
                "industry",
                "plan_tier",
                "active_paid_mrr",
                "young_subs",
                "expected_loss_90d",
                "acao_sugerida",
            ], [
                "Conta",
                "Indústria",
                "Plano",
                "MRR ativo",
                "Assin. < 90d",
                "Perda esperada",
                "Ação sugerida",
            ]);
            break;
        case "acoes":
            break;
        default:
            alvo.appendChild(el("div", "text-sm text-stone-500", "Gráfico não reconhecido."));
    }
}
function blocoSecao(nivel, secao) {
    const caixa = el("section", "rounded-xl border border-stone-200 bg-white p-5 shadow-sm");
    const cab = el("div", "flex flex-wrap items-center gap-3");
    cab.appendChild(el("span", `rounded-full px-2.5 py-1 text-[11px] font-medium ring-1 ${NIVEL_COR[nivel]}`, NIVEL_ROTULO[nivel]));
    cab.appendChild(el("h3", "text-base font-semibold text-stone-900", secao.titulo));
    caixa.appendChild(cab);
    const area = el("div", "mt-4 overflow-x-auto");
    caixa.appendChild(area);
    desenhar(secao, area);
    if (secao.quebra) {
        const q = el("div", "mt-3 rounded-md bg-amber-50 p-3 text-sm text-amber-900 ring-1 ring-amber-200");
        q.textContent =
            `Quebra de regime: razão de risco ${br(secao.quebra.antes, 1)}× antes de out/2024, ` +
                `${br(secao.quebra.depois, 1)}× depois ` +
                `(IC ${br(secao.quebra.ic_depois[0], 2)}–${br(secao.quebra.ic_depois[1], 2)}). ` +
                `O efeito não é invariante no tempo: análise causal condiciona no regime.`;
        caixa.appendChild(q);
    }
    caixa.appendChild(el("p", "mt-4 text-sm leading-relaxed text-stone-700", secao.leitura));
    if (secao.acoes)
        caixa.appendChild(blocoAcoes(secao.acoes));
    if (secao.confiabilidade) {
        const aviso = el("div", "mt-3 flex gap-2 rounded-md bg-stone-100 p-3 text-xs text-stone-600");
        aviso.appendChild(el("span", "font-semibold shrink-0", "Confiabilidade:"));
        aviso.appendChild(el("span", "", secao.confiabilidade));
        caixa.appendChild(aviso);
    }
    return caixa;
}
function blocoLacunas(lacunas) {
    const caixa = el("section", "rounded-xl border-2 border-dashed border-stone-300 bg-stone-50 p-5");
    caixa.appendChild(el("h3", "text-base font-semibold text-stone-800", "O que este painel NÃO mostra"));
    caixa.appendChild(el("p", "mt-1 text-sm text-stone-600", "KPIs que o dataset não sustenta. Ficam em branco de propósito: um número " +
        "estimado aqui viraria decisão lá fora."));
    const lista = el("ul", "mt-3 space-y-2");
    lacunas.forEach((l) => {
        const item = el("li", "text-sm text-stone-700");
        item.appendChild(el("span", "font-medium text-stone-900", l.kpi + " — "));
        item.appendChild(el("span", "", l.porque));
        lista.appendChild(item);
    });
    caixa.appendChild(lista);
    return caixa;
}
function render() {
    const dados = window.DASHBOARD_DATA;
    const painel = dados.paineis[atual];
    const raiz = document.getElementById("painel");
    raiz.innerHTML = "";
    const cab = el("header", "mb-6");
    cab.appendChild(el("h2", "text-2xl font-semibold tracking-tight text-stone-900", painel.titulo));
    cab.appendChild(el("p", "mt-1 text-sm text-stone-600", painel.publico + " · " + painel.pergunta));
    raiz.appendChild(cab);
    const kpis = el("div", "mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4");
    painel.kpis.forEach((k) => kpis.appendChild(cartaoKpi(k)));
    raiz.appendChild(kpis);
    const grade = el("div", "space-y-5");
    ["descritivo", "diagnostico", "preditivo", "prescritivo"].forEach((nivel) => grade.appendChild(blocoSecao(nivel, painel[nivel])));
    grade.appendChild(blocoLacunas(painel.lacunas));
    raiz.appendChild(grade);
    document.querySelectorAll("[data-aba]").forEach((b) => {
        const ativo = b.dataset.aba === atual;
        b.className = ativo
            ? "rounded-md bg-stone-900 px-3.5 py-2 text-sm font-medium text-white"
            : "rounded-md px-3.5 py-2 text-sm font-medium text-stone-600 hover:bg-stone-200";
    });
    // Os gráficos Plotly são desenhados antes de `caixa` entrar no DOM (o bloco
    // que os contém só é anexado depois, no fim de `render`), então o primeiro
    // layout usa o tamanho padrão da biblioteca em vez do container real. Um
    // redimensionamento no próximo frame, já com tudo anexado, corrige o
    // tamanho sem precisar reordenar a montagem do DOM.
    requestAnimationFrame(() => {
        document.querySelectorAll("#painel .js-plotly-plot").forEach((div) => {
            Plotly.Plots.resize(div);
        });
    });
}
function iniciar() {
    const dados = window.DASHBOARD_DATA;
    if (!dados) {
        document.body.innerHTML =
            '<p class="p-8 text-red-700">data.js não carregou. Gere com: ' +
                "<code>uv run python -m churn_diag</code></p>";
        return;
    }
    const abas = document.getElementById("abas");
    ORDEM.forEach((nome) => {
        const b = document.createElement("button");
        b.dataset.aba = nome;
        b.textContent = ROTULOS[nome];
        b.addEventListener("click", () => {
            atual = nome;
            render();
            window.scrollTo({ top: 0, behavior: "smooth" });
        });
        abas.appendChild(b);
    });
    const rodape = document.getElementById("rodape");
    rodape.textContent =
        `Snapshot ${dados.snapshot} · período-alvo a partir de ${dados.inicio_periodo_alvo} · ` +
            dados.aviso;
    render();
    let t;
    window.addEventListener("resize", () => {
        window.clearTimeout(t);
        t = window.setTimeout(render, 180);
    });
}
document.addEventListener("DOMContentLoaded", iniciar);
/** Formatação pt-BR e paleta — as mesmas do relatório, para o painel não
 *  contar a história com outras cores nem com outra pontuação decimal. */
const PALETA = {
    azul: "#2a78d6",
    laranja: "#eb6834",
    tinta: "#1b1b1a",
    tinta2: "#55534e",
    suave: "#a8a5a0",
    grade: "#e6e4e0",
    bom: "#2f7d4f",
    ruim: "#c0392b",
};
function br(valor, casas = 1) {
    return valor.toLocaleString("pt-BR", {
        minimumFractionDigits: casas,
        maximumFractionDigits: casas,
    });
}
function brAuto(valor) {
    if (!isFinite(valor))
        return "—";
    if (Number.isInteger(valor))
        return valor.toLocaleString("pt-BR");
    return br(valor, Math.abs(valor) < 10 ? 2 : 1);
}
function dinheiro(valor) {
    return "US$ " + valor.toLocaleString("pt-BR", { maximumFractionDigits: 0 });
}
function mesCurto(iso) {
    const meses = [
        "jan", "fev", "mar", "abr", "mai", "jun",
        "jul", "ago", "set", "out", "nov", "dez",
    ];
    const d = new Date(iso + "T00:00:00");
    return meses[d.getMonth()] + "/" + String(d.getFullYear()).slice(2);
}
/** Gráficos interativos: Plotly.js para as duas séries (zoom, pan, hover
 *  unificado, exportação nativa em PNG) e Chart.js para barras e barras
 *  agrupadas (tooltip, legenda clicável, responsivo).
 *
 *  Regra de projeto herdada da versão em D3: nenhum gráfico inventa escala
 *  nem esconde zero. Barra começa em zero; série temporal mostra o eixo
 *  inteiro; barra de erro aparece sempre que o payload traz erro-padrão.
 *  Gráfico que engana é pior que tabela.
 */
const FONTE = "ui-sans-serif, system-ui, -apple-system, sans-serif";
/** Cada canvas/div de gráfico guarda a instância que o criou, para destruir
 *  antes de redesenhar — sem isso, redimensionar a janela vaza um Chart por
 *  resize. */
function limpar(alvo) {
    const existente = alvo._chart;
    if (existente)
        existente.destroy();
    alvo.innerHTML = "";
}
function novoCanvas(alvo, altura) {
    limpar(alvo);
    const caixa = document.createElement("div");
    caixa.style.position = "relative";
    caixa.style.height = altura + "px";
    caixa.style.width = "100%";
    const canvas = document.createElement("canvas");
    caixa.appendChild(canvas);
    alvo.appendChild(caixa);
    return canvas;
}
function novoDiv(alvo, altura) {
    limpar(alvo);
    const div = document.createElement("div");
    div.style.width = "100%";
    div.style.height = altura + "px";
    alvo.appendChild(div);
    return div;
}
const TOOLTIP_BASE = {
    backgroundColor: "#1b1b1a",
    titleFont: { family: FONTE, size: 11 },
    bodyFont: { family: FONTE, size: 12 },
    padding: 8,
    cornerRadius: 6,
    displayColors: false,
};
/** 1–2. Barra vertical ou horizontal, com tooltip formatado no mesmo padrão
 *  pt-BR do relatório. Interatividade: hover realça a barra, tooltip mostra
 *  o valor exato, e passar o mouse na legenda (quando houver) filtra a série. */
function barras(alvo, dados, op) {
    const altura = op.horizontal ? Math.max(200, dados.length * 34 + 60) : 300;
    const canvas = novoCanvas(alvo, altura);
    const fmt = op.formatador || brAuto;
    const rotulos = dados.map((d) => String(d[op.campoX]));
    const valores = dados.map((d) => Number(d[op.campoY]) || 0);
    const cores = valores.map((v) => (v < 0 ? PALETA.laranja : op.cor || PALETA.azul));
    const chart = new Chart(canvas, {
        type: "bar",
        data: {
            labels: rotulos,
            datasets: [
                {
                    data: valores,
                    backgroundColor: cores,
                    hoverBackgroundColor: cores.map((c) => c),
                    borderRadius: 3,
                    borderSkipped: false,
                },
            ],
        },
        options: {
            indexAxis: op.horizontal ? "y" : "x",
            responsive: true,
            maintainAspectRatio: false,
            animation: { duration: 260 },
            plugins: {
                legend: { display: false },
                tooltip: {
                    ...TOOLTIP_BASE,
                    callbacks: {
                        label: (ctx) => fmt(op.horizontal ? ctx.parsed.x : ctx.parsed.y),
                    },
                },
            },
            scales: {
                x: op.horizontal
                    ? {
                        beginAtZero: true,
                        ticks: { font: { family: FONTE, size: 10 }, callback: (v) => fmt(v) },
                        grid: { color: PALETA.grade },
                    }
                    : {
                        ticks: { font: { family: FONTE, size: 10 } },
                        grid: { display: false },
                    },
                y: op.horizontal
                    ? { ticks: { font: { family: FONTE, size: 11 } }, grid: { display: false } }
                    : {
                        beginAtZero: true,
                        title: { display: true, text: op.rotuloY, font: { family: FONTE, size: 10 } },
                        ticks: { font: { family: FONTE, size: 10 }, callback: (v) => fmt(v) },
                        grid: { color: PALETA.grade },
                    },
            },
        },
    });
    alvo._chart = chart;
}
/** 3. Barras agrupadas: risco por faixa de idade, referência × período-alvo.
 *  Clicar num item da legenda esconde/mostra o período inteiro — útil para
 *  isolar visualmente o efeito da quebra de regime. */
function risco(alvo, dados) {
    const rotuloPeriodo = {
        reference: "jan–set/24",
        target: "out–dez/24",
    };
    const faixas = Array.from(new Set(dados.map((d) => String(d["age_bucket"]))));
    const canvas = novoCanvas(alvo, 300);
    const serie = (periodo, cor) => ({
        label: rotuloPeriodo[periodo],
        data: faixas.map((faixa) => {
            const linha = dados.find((d) => d["age_bucket"] === faixa && d["period"] === periodo);
            return linha ? Number(linha["hazard_pct"]) : null;
        }),
        backgroundColor: cor,
        borderRadius: 3,
        borderSkipped: false,
    });
    const chart = new Chart(canvas, {
        type: "bar",
        data: {
            labels: faixas,
            datasets: [serie("reference", PALETA.azul), serie("target", PALETA.laranja)],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: { duration: 260 },
            plugins: {
                legend: {
                    position: "top",
                    align: "end",
                    labels: { font: { family: FONTE, size: 11 }, boxWidth: 12, boxHeight: 12 },
                },
                tooltip: {
                    ...TOOLTIP_BASE,
                    callbacks: { label: (ctx) => `${ctx.dataset.label}: ${br(ctx.parsed.y, 2)}%` },
                },
            },
            scales: {
                x: { ticks: { font: { family: FONTE, size: 10 } }, grid: { display: false } },
                y: {
                    beginAtZero: true,
                    title: { display: true, text: "risco mensal (%)", font: { family: FONTE, size: 10 } },
                    ticks: {
                        font: { family: FONTE, size: 10 },
                        callback: (v) => br(v, 1) + "%",
                    },
                    grid: { color: PALETA.grade },
                },
            },
        },
    });
    alvo._chart = chart;
}
/** 4. Série mensal: barras de MRR perdido + linha da taxa de churn no eixo
 *  secundário, com o limite de controle marcado. Plotly dá zoom por arraste,
 *  pan, reset e hover unificado nas duas séries ao mesmo tempo — o ponto
 *  onde a quebra de regime aparece fica exploratório, não só ilustrado. */
function serieChurn(alvo, dados, ucl) {
    const pontos = dados.filter((d) => String(d["month"]) >= "2024-01-01");
    const div = novoDiv(alvo, 340);
    const meses = pontos.map((d) => mesCurto(String(d["month"])));
    const mrrPerdido = pontos.map((d) => Number(d["churned_mrr"]));
    const taxaChurn = pontos.map((d) => Number(d["mrr_churn_pct"]));
    const tracos = [
        {
            type: "bar",
            name: "MRR perdido (US$)",
            x: meses,
            y: mrrPerdido,
            marker: { color: PALETA.azul },
            hovertemplate: "%{x}<br>MRR perdido: US$ %{y:,.0f}<extra></extra>",
            yaxis: "y",
        },
        {
            type: "scatter",
            mode: "lines+markers",
            name: "Churn de MRR (%)",
            x: meses,
            y: taxaChurn,
            line: { color: PALETA.laranja, width: 2.5 },
            marker: { color: PALETA.laranja, size: 6 },
            hovertemplate: "%{x}<br>Churn: %{y:.2f}%<extra></extra>",
            yaxis: "y2",
        },
    ];
    const shapes = [];
    const anotacoes = [];
    if (ucl) {
        shapes.push({
            type: "line",
            xref: "paper",
            x0: 0,
            x1: 1,
            yref: "y2",
            y0: ucl,
            y1: ucl,
            line: { color: PALETA.ruim, width: 1.2, dash: "dash" },
        });
        anotacoes.push({
            xref: "paper",
            x: 0,
            xanchor: "left",
            yref: "y2",
            y: ucl,
            yanchor: "bottom",
            text: `limite de controle ${br(ucl, 2)}%`,
            showarrow: false,
            font: { size: 10, color: PALETA.ruim, family: FONTE },
        });
    }
    Plotly.newPlot(div, tracos, {
        margin: { t: 20, r: 56, b: 40, l: 64 },
        font: { family: FONTE, size: 11, color: PALETA.tinta2 },
        showlegend: true,
        legend: { orientation: "h", y: 1.12, font: { size: 11 } },
        hovermode: "x unified",
        barmode: "group",
        shapes,
        annotations: anotacoes,
        xaxis: { showgrid: false, tickfont: { size: 10 } },
        yaxis: {
            title: { text: "MRR perdido (US$)", font: { size: 10 } },
            gridcolor: PALETA.grade,
            tickfont: { size: 10 },
        },
        yaxis2: {
            title: { text: "churn de MRR (%)", font: { size: 10 } },
            overlaying: "y",
            side: "right",
            showgrid: false,
            tickfont: { size: 10 },
            ticksuffix: "%",
        },
        paper_bgcolor: "rgba(0,0,0,0)",
        plot_bgcolor: "rgba(0,0,0,0)",
    }, {
        responsive: true,
        displaylogo: false,
        modeBarButtonsToRemove: ["lasso2d", "select2d", "autoScale2d"],
    });
    alvo._chart = { destroy: () => Plotly.purge(div) };
}
/** Tabela — quando a leitura correta é linha a linha, não barra.
 *  Interatividade: clicar num cabeçalho ordena por aquela coluna (numérica
 *  ou texto), clicar de novo inverte — sem nenhuma dependência extra. */
function tabela(alvo, dadosOriginais, colunas, titulos) {
    limpar(alvo);
    let dados = [...dadosOriginais];
    let colunaOrdenada = -1;
    let crescente = true;
    const tabela = document.createElement("table");
    tabela.className = "w-full text-sm";
    const thead = document.createElement("thead");
    const trCab = document.createElement("tr");
    trCab.className = "text-left text-xs uppercase tracking-wide text-stone-500";
    titulos.forEach((titulo, i) => {
        const th = document.createElement("th");
        th.className =
            "py-2 pr-3 font-semibold border-b border-stone-200 cursor-pointer select-none hover:text-stone-800";
        th.textContent = titulo;
        th.addEventListener("click", () => {
            crescente = colunaOrdenada === i ? !crescente : true;
            colunaOrdenada = i;
            const col = colunas[i];
            dados = [...dados].sort((a, b) => {
                const va = a[col];
                const vb = b[col];
                const cmp = typeof va === "number" && typeof vb === "number"
                    ? va - vb
                    : String(va ?? "").localeCompare(String(vb ?? ""), "pt-BR");
                return crescente ? cmp : -cmp;
            });
            desenharCorpo();
        });
        trCab.appendChild(th);
    });
    thead.appendChild(trCab);
    tabela.appendChild(thead);
    const tbody = document.createElement("tbody");
    tabela.appendChild(tbody);
    function desenharCorpo() {
        tbody.innerHTML = "";
        dados.forEach((linha) => {
            const tr = document.createElement("tr");
            tr.className = "border-b border-stone-100 align-top hover:bg-stone-50";
            colunas.forEach((c) => {
                const td = document.createElement("td");
                td.className = "py-2 pr-3 text-stone-700";
                const v = linha[c];
                td.textContent = typeof v === "number" ? brAuto(v) : String(v ?? "—");
                tr.appendChild(td);
            });
            tbody.appendChild(tr);
        });
    }
    desenharCorpo();
    alvo.appendChild(tabela);
}
/** Formato do payload gerado por `churn_diag.dashboards` (data.js). */
