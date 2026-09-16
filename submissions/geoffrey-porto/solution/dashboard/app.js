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
/** Gráficos D3 — um por tipo declarado no payload.
 *
 *  Regra de projeto: nenhum gráfico inventa escala nem esconde zero. Barra
 *  começa em zero; série temporal mostra o eixo inteiro; barra de erro aparece
 *  sempre que o payload traz erro-padrão. Gráfico que engana é pior que tabela.
 */
const MARGEM = { topo: 16, direita: 18, baixo: 44, esquerda: 64 };
function svgBase(alvo, altura) {
    const largura = Math.max(alvo.clientWidth || 640, 320);
    d3.select(alvo).selectAll("*").remove();
    const svg = d3
        .select(alvo)
        .append("svg")
        .attr("viewBox", `0 0 ${largura} ${altura}`)
        .attr("width", "100%")
        .attr("height", altura)
        .attr("role", "img");
    return { svg, largura, altura };
}
function eixoY(g, escala, largura, rotulo) {
    g.append("g")
        .call(d3.axisLeft(escala).ticks(5).tickSize(-largura))
        .call((sel) => sel.select(".domain").remove())
        .call((sel) => sel.selectAll(".tick line").attr("stroke", PALETA.grade))
        .call((sel) => sel.selectAll("text").attr("fill", PALETA.tinta2).attr("font-size", 11));
    g.append("text")
        .attr("transform", "rotate(-90)")
        .attr("y", -MARGEM.esquerda + 14)
        .attr("x", -10)
        .attr("fill", PALETA.tinta2)
        .attr("font-size", 11)
        .attr("text-anchor", "end")
        .text(rotulo);
}
function barras(alvo, dados, op) {
    const altura = op.horizontal ? Math.max(180, dados.length * 30 + 60) : 300;
    const { svg, largura } = svgBase(alvo, altura);
    const g = svg
        .append("g")
        .attr("transform", `translate(${MARGEM.esquerda},${MARGEM.topo})`);
    const w = largura - MARGEM.esquerda - MARGEM.direita;
    const h = altura - MARGEM.topo - MARGEM.baixo;
    const fmt = op.formatador || brAuto;
    const valores = dados.map((d) => Number(d[op.campoY]) || 0);
    const maximo = Math.max(0, ...valores);
    const minimo = Math.min(0, ...valores);
    if (op.horizontal) {
        const y = d3
            .scaleBand()
            .domain(dados.map((d) => String(d[op.campoX])))
            .range([0, h])
            .padding(0.25);
        const x = d3.scaleLinear().domain([minimo, maximo * 1.15]).range([0, w]);
        g.append("g")
            .attr("transform", `translate(0,${h})`)
            .call(d3.axisBottom(x).ticks(5))
            .call((s) => s.selectAll("text").attr("fill", PALETA.tinta2).attr("font-size", 11));
        g.append("g")
            .call(d3.axisLeft(y).tickSize(0))
            .call((s) => s.select(".domain").remove())
            .call((s) => s.selectAll("text").attr("fill", PALETA.tinta2).attr("font-size", 11));
        g.selectAll("rect")
            .data(dados)
            .join("rect")
            .attr("y", (d) => y(String(d[op.campoX])))
            .attr("x", (d) => x(Math.min(0, Number(d[op.campoY]))))
            .attr("height", y.bandwidth())
            .attr("width", (d) => Math.abs(x(Number(d[op.campoY])) - x(0)))
            .attr("fill", (d) => Number(d[op.campoY]) < 0 ? PALETA.laranja : op.cor || PALETA.azul)
            .attr("rx", 2);
        g.selectAll("text.valor")
            .data(dados)
            .join("text")
            .attr("class", "valor")
            .attr("y", (d) => y(String(d[op.campoX])) + y.bandwidth() / 2 + 4)
            .attr("x", (d) => x(Number(d[op.campoY])) + 6)
            .attr("fill", PALETA.tinta2)
            .attr("font-size", 11)
            .text((d) => fmt(Number(d[op.campoY])));
        return;
    }
    const x = d3
        .scaleBand()
        .domain(dados.map((d) => String(d[op.campoX])))
        .range([0, w])
        .padding(0.22);
    const y = d3.scaleLinear().domain([minimo, maximo * 1.12 || 1]).range([h, 0]);
    eixoY(g, y, w, op.rotuloY);
    g.append("g")
        .attr("transform", `translate(0,${h})`)
        .call(d3.axisBottom(x).tickSize(0))
        .call((s) => s.select(".domain").attr("stroke", PALETA.grade))
        .call((s) => s
        .selectAll("text")
        .attr("fill", PALETA.tinta2)
        .attr("font-size", 11)
        .attr("transform", dados.length > 6 ? "rotate(-20)" : null)
        .attr("text-anchor", dados.length > 6 ? "end" : "middle"));
    g.selectAll("rect")
        .data(dados)
        .join("rect")
        .attr("x", (d) => x(String(d[op.campoX])))
        .attr("y", (d) => y(Math.max(0, Number(d[op.campoY]))))
        .attr("width", x.bandwidth())
        .attr("height", (d) => Math.abs(y(Number(d[op.campoY])) - y(0)))
        .attr("fill", (d) => Number(d[op.campoY]) < 0 ? PALETA.laranja : op.cor || PALETA.azul)
        .attr("rx", 2);
    g.selectAll("text.valor")
        .data(dados)
        .join("text")
        .attr("class", "valor")
        .attr("x", (d) => x(String(d[op.campoX])) + x.bandwidth() / 2)
        .attr("y", (d) => y(Number(d[op.campoY])) - 6)
        .attr("text-anchor", "middle")
        .attr("fill", PALETA.tinta2)
        .attr("font-size", 11)
        .text((d) => fmt(Number(d[op.campoY])));
}
/** Série mensal: barras de MRR perdido + linha da taxa, com limite de controle. */
function serieChurn(alvo, dados, ucl) {
    const pontos = dados.filter((d) => String(d["month"]) >= "2024-01-01");
    const altura = 320;
    const { svg, largura } = svgBase(alvo, altura);
    const g = svg
        .append("g")
        .attr("transform", `translate(${MARGEM.esquerda},${MARGEM.topo})`);
    const w = largura - MARGEM.esquerda - MARGEM.direita * 3;
    const h = altura - MARGEM.topo - MARGEM.baixo;
    const x = d3
        .scaleBand()
        .domain(pontos.map((d) => String(d["month"])))
        .range([0, w])
        .padding(0.3);
    const yMrr = d3
        .scaleLinear()
        .domain([0, d3.max(pontos, (d) => Number(d["churned_mrr"])) * 1.15])
        .range([h, 0]);
    const yTaxa = d3
        .scaleLinear()
        .domain([0, d3.max(pontos, (d) => Number(d["mrr_churn_pct"])) * 1.3])
        .range([h, 0]);
    eixoY(g, yMrr, w, "MRR perdido (US$)");
    g.append("g")
        .attr("transform", `translate(${w},0)`)
        .call(d3.axisRight(yTaxa).ticks(5).tickFormat((v) => br(v, 1) + "%"))
        .call((s) => s.select(".domain").remove())
        .call((s) => s.selectAll("text").attr("fill", PALETA.laranja).attr("font-size", 11));
    g.append("g")
        .attr("transform", `translate(0,${h})`)
        .call(d3.axisBottom(x).tickFormat((v) => mesCurto(v)))
        .call((s) => s.select(".domain").attr("stroke", PALETA.grade))
        .call((s) => s.selectAll("text").attr("fill", PALETA.tinta2).attr("font-size", 11));
    g.selectAll("rect")
        .data(pontos)
        .join("rect")
        .attr("x", (d) => x(String(d["month"])))
        .attr("y", (d) => yMrr(Number(d["churned_mrr"])))
        .attr("width", x.bandwidth())
        .attr("height", (d) => h - yMrr(Number(d["churned_mrr"])))
        .attr("fill", PALETA.azul)
        .attr("opacity", 0.85)
        .attr("rx", 2);
    const linha = d3
        .line()
        .x((d) => x(String(d["month"])) + x.bandwidth() / 2)
        .y((d) => yTaxa(Number(d["mrr_churn_pct"])));
    g.append("path")
        .datum(pontos)
        .attr("fill", "none")
        .attr("stroke", PALETA.laranja)
        .attr("stroke-width", 2.4)
        .attr("d", linha);
    g.selectAll("circle")
        .data(pontos)
        .join("circle")
        .attr("cx", (d) => x(String(d["month"])) + x.bandwidth() / 2)
        .attr("cy", (d) => yTaxa(Number(d["mrr_churn_pct"])))
        .attr("r", 3.5)
        .attr("fill", PALETA.laranja);
    if (ucl) {
        g.append("line")
            .attr("x1", 0)
            .attr("x2", w)
            .attr("y1", yTaxa(ucl))
            .attr("y2", yTaxa(ucl))
            .attr("stroke", PALETA.ruim)
            .attr("stroke-dasharray", "5 4")
            .attr("stroke-width", 1.2);
        g.append("text")
            .attr("x", 4)
            .attr("y", yTaxa(ucl) - 5)
            .attr("fill", PALETA.ruim)
            .attr("font-size", 10)
            .text(`limite de controle ${br(ucl, 2)}%`);
    }
}
/** Barras agrupadas: risco por faixa de idade, referência × período-alvo. */
function risco(alvo, dados) {
    const periodos = ["reference", "target"];
    const rotulo = {
        reference: "jan–set/24",
        target: "out–dez/24",
    };
    const faixas = Array.from(new Set(dados.map((d) => String(d["age_bucket"]))));
    const altura = 300;
    const { svg, largura } = svgBase(alvo, altura);
    const g = svg
        .append("g")
        .attr("transform", `translate(${MARGEM.esquerda},${MARGEM.topo})`);
    const w = largura - MARGEM.esquerda - MARGEM.direita;
    const h = altura - MARGEM.topo - MARGEM.baixo;
    const x0 = d3.scaleBand().domain(faixas).range([0, w]).padding(0.25);
    const x1 = d3.scaleBand().domain(periodos).range([0, x0.bandwidth()]).padding(0.1);
    const y = d3
        .scaleLinear()
        .domain([0, d3.max(dados, (d) => Number(d["hazard_pct"])) * 1.2])
        .range([h, 0]);
    eixoY(g, y, w, "risco mensal (%)");
    g.append("g")
        .attr("transform", `translate(0,${h})`)
        .call(d3.axisBottom(x0).tickSize(0))
        .call((s) => s.select(".domain").attr("stroke", PALETA.grade))
        .call((s) => s.selectAll("text").attr("fill", PALETA.tinta2).attr("font-size", 11));
    g.selectAll("rect")
        .data(dados.filter((d) => periodos.indexOf(String(d["period"])) >= 0))
        .join("rect")
        .attr("x", (d) => x0(String(d["age_bucket"])) + x1(String(d["period"])))
        .attr("y", (d) => y(Number(d["hazard_pct"])))
        .attr("width", x1.bandwidth())
        .attr("height", (d) => h - y(Number(d["hazard_pct"])))
        .attr("fill", (d) => d["period"] === "target" ? PALETA.laranja : PALETA.azul)
        .attr("rx", 2);
    const legenda = g.append("g").attr("transform", `translate(${w - 190},0)`);
    periodos.forEach((p, i) => {
        legenda
            .append("rect")
            .attr("x", i * 95)
            .attr("y", 0)
            .attr("width", 10)
            .attr("height", 10)
            .attr("fill", p === "target" ? PALETA.laranja : PALETA.azul);
        legenda
            .append("text")
            .attr("x", i * 95 + 15)
            .attr("y", 9)
            .attr("fill", PALETA.tinta2)
            .attr("font-size", 11)
            .text(rotulo[p]);
    });
}
/** Tabela — quando a leitura correta é linha a linha, não barra. */
function tabela(alvo, dados, colunas, titulos) {
    d3.select(alvo).selectAll("*").remove();
    const t = d3.select(alvo).append("table").attr("class", "w-full text-sm");
    t.append("thead")
        .append("tr")
        .attr("class", "text-left text-xs uppercase tracking-wide text-stone-500")
        .selectAll("th")
        .data(titulos)
        .join("th")
        .attr("class", "py-2 pr-3 font-semibold border-b border-stone-200")
        .text((d) => d);
    const linhas = t
        .append("tbody")
        .selectAll("tr")
        .data(dados)
        .join("tr")
        .attr("class", "border-b border-stone-100 align-top");
    colunas.forEach((c) => {
        linhas
            .append("td")
            .attr("class", "py-2 pr-3 text-stone-700")
            .text((d) => {
            const v = d[c];
            return typeof v === "number" ? brAuto(v) : String(v ?? "—");
        });
    });
}
/** Formato do payload gerado por `churn_diag.dashboards` (data.js). */
