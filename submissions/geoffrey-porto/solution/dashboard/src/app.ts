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

const ORDEM: string[] = ["ceo", "vendas", "marketing", "financeiro", "operacoes"];
const ROTULOS: { [k: string]: string } = {
  ceo: "CEO",
  vendas: "Vendas",
  marketing: "Marketing",
  financeiro: "Financeiro",
  operacoes: "Operações / CS",
};
const NIVEL_ROTULO: { [k: string]: string } = {
  descritivo: "Descritivo · o que aconteceu",
  diagnostico: "Diagnóstico · por que aconteceu",
  preditivo: "Preditivo · o que vem",
  prescritivo: "Prescritivo · o que fazer",
};
const NIVEL_COR: { [k: string]: string } = {
  descritivo: "bg-sky-50 text-sky-800 ring-sky-200",
  diagnostico: "bg-amber-50 text-amber-800 ring-amber-200",
  preditivo: "bg-violet-50 text-violet-800 ring-violet-200",
  prescritivo: "bg-emerald-50 text-emerald-800 ring-emerald-200",
};

let atual = "ceo";

function el(tag: string, classe: string, texto?: string): HTMLElement {
  const n = document.createElement(tag);
  n.className = classe;
  if (texto !== undefined) n.textContent = texto;
  return n;
}

function cartaoKpi(k: Kpi): HTMLElement {
  const cor =
    k.direcao === "ruim"
      ? "text-red-700"
      : k.direcao === "bom"
        ? "text-emerald-700"
        : "text-stone-900";
  const cartao = el(
    "div",
    "rounded-lg border border-stone-200 bg-white p-4 shadow-sm"
  );
  cartao.appendChild(
    el("div", "text-xs uppercase tracking-wide text-stone-500", k.rotulo)
  );
  const valor = el("div", `mt-1 text-2xl font-semibold tabular-nums ${cor}`);
  valor.textContent = brAuto(k.valor) + (k.unidade ? " " + k.unidade : "");
  cartao.appendChild(valor);
  if (k.nota) cartao.appendChild(el("div", "mt-1 text-xs text-stone-500", k.nota));
  if (k.chave) {
    const t = el(
      "div",
      "mt-2 font-mono text-[10px] text-stone-400",
      "metrics.json → " + k.chave
    );
    t.title = "Toda métrica do painel tem origem rastreável no pipeline";
    cartao.appendChild(t);
  }
  return cartao;
}

function blocoAcoes(acoes: Acao[]): HTMLElement {
  const lista = el("div", "mt-3 space-y-3");
  acoes.forEach((a) => {
    const item = el(
      "div",
      "rounded-md border border-stone-200 bg-stone-50 p-3"
    );
    const cab = el("div", "flex items-start justify-between gap-3");
    cab.appendChild(el("div", "font-medium text-stone-900", a.acao));
    const cores: { [k: string]: string } = {
      alta: "bg-emerald-100 text-emerald-800",
      media: "bg-amber-100 text-amber-800",
      baixa: "bg-stone-200 text-stone-700",
    };
    cab.appendChild(
      el(
        "span",
        `shrink-0 rounded px-2 py-0.5 text-[11px] font-medium ${cores[a.confianca]}`,
        "confiança " + a.confianca
      )
    );
    item.appendChild(cab);
    item.appendChild(el("div", "mt-1 text-sm text-stone-600", a.porque));
    lista.appendChild(item);
  });
  return lista;
}

/** Escolhe o gráfico pelo tipo declarado no payload. */
function desenhar(secao: Secao, alvo: HTMLElement): void {
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
        formatador: (v: number) => br(v, 1) + "%",
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
      tabela(
        alvo,
        d,
        [
          "priority",
          "tickets",
          "resolucao_mediana_h",
          "primeira_resposta_mediana_min",
          "escalacao_pct",
          "csat_medio",
          "sem_csat_pct",
        ],
        [
          "Prioridade",
          "Tickets",
          "Resolução (h)",
          "1ª resposta (min)",
          "Escalação (%)",
          "CSAT",
          "Sem CSAT (%)",
        ]
      );
      break;
    case "erros_feature":
      barras(alvo, d, {
        campoX: "feature_name",
        campoY: "erros_por_100_usos",
        rotuloY: "erros por 100 usos",
        cor: PALETA.laranja,
        horizontal: true,
        formatador: (v: number) => br(v, 2),
      });
      break;
    case "motivos":
      barras(alvo, d, {
        campoX: "reason_code",
        campoY: "share_pct",
        rotuloY: "participação (%)",
        formatador: (v: number) => br(v, 1) + "%",
      });
      break;
    case "fila_cs":
      tabela(
        alvo,
        d,
        [
          "account_name",
          "industry",
          "plan_tier",
          "active_paid_mrr",
          "young_subs",
          "expected_loss_90d",
          "acao_sugerida",
        ],
        [
          "Conta",
          "Indústria",
          "Plano",
          "MRR ativo",
          "Assin. < 90d",
          "Perda esperada",
          "Ação sugerida",
        ]
      );
      break;
    case "acoes":
      break;
    default:
      alvo.appendChild(
        el("div", "text-sm text-stone-500", "Gráfico não reconhecido.")
      );
  }
}

function blocoSecao(nivel: string, secao: Secao): HTMLElement {
  const caixa = el(
    "section",
    "rounded-xl border border-stone-200 bg-white p-5 shadow-sm"
  );
  const cab = el("div", "flex flex-wrap items-center gap-3");
  cab.appendChild(
    el(
      "span",
      `rounded-full px-2.5 py-1 text-[11px] font-medium ring-1 ${NIVEL_COR[nivel]}`,
      NIVEL_ROTULO[nivel]
    )
  );
  cab.appendChild(el("h3", "text-base font-semibold text-stone-900", secao.titulo));
  caixa.appendChild(cab);

  const area = el("div", "mt-4 overflow-x-auto");
  caixa.appendChild(area);
  desenhar(secao, area);

  if (secao.quebra) {
    const q = el(
      "div",
      "mt-3 rounded-md bg-amber-50 p-3 text-sm text-amber-900 ring-1 ring-amber-200"
    );
    q.textContent =
      `Quebra de regime: razão de risco ${br(secao.quebra.antes, 1)}× antes de out/2024, ` +
      `${br(secao.quebra.depois, 1)}× depois ` +
      `(IC ${br(secao.quebra.ic_depois[0], 2)}–${br(secao.quebra.ic_depois[1], 2)}). ` +
      `O efeito não é invariante no tempo: análise causal condiciona no regime.`;
    caixa.appendChild(q);
  }

  caixa.appendChild(el("p", "mt-4 text-sm leading-relaxed text-stone-700", secao.leitura));

  if (secao.acoes) caixa.appendChild(blocoAcoes(secao.acoes));

  if (secao.confiabilidade) {
    const aviso = el(
      "div",
      "mt-3 flex gap-2 rounded-md bg-stone-100 p-3 text-xs text-stone-600"
    );
    aviso.appendChild(el("span", "font-semibold shrink-0", "Confiabilidade:"));
    aviso.appendChild(el("span", "", secao.confiabilidade));
    caixa.appendChild(aviso);
  }
  return caixa;
}

function blocoLacunas(lacunas: Lacuna[]): HTMLElement {
  const caixa = el(
    "section",
    "rounded-xl border-2 border-dashed border-stone-300 bg-stone-50 p-5"
  );
  caixa.appendChild(
    el("h3", "text-base font-semibold text-stone-800", "O que este painel NÃO mostra")
  );
  caixa.appendChild(
    el(
      "p",
      "mt-1 text-sm text-stone-600",
      "KPIs que o dataset não sustenta. Ficam em branco de propósito: um número " +
        "estimado aqui viraria decisão lá fora."
    )
  );
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

function render(): void {
  const dados = window.DASHBOARD_DATA;
  const painel = dados.paineis[atual];
  const raiz = document.getElementById("painel") as HTMLElement;
  raiz.innerHTML = "";

  const cab = el("header", "mb-6");
  cab.appendChild(
    el("h2", "text-2xl font-semibold tracking-tight text-stone-900", painel.titulo)
  );
  cab.appendChild(
    el("p", "mt-1 text-sm text-stone-600", painel.publico + " · " + painel.pergunta)
  );
  raiz.appendChild(cab);

  const kpis = el("div", "mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4");
  painel.kpis.forEach((k) => kpis.appendChild(cartaoKpi(k)));
  raiz.appendChild(kpis);

  const grade = el("div", "space-y-5");
  (["descritivo", "diagnostico", "preditivo", "prescritivo"] as const).forEach(
    (nivel) => grade.appendChild(blocoSecao(nivel, painel[nivel]))
  );
  grade.appendChild(blocoLacunas(painel.lacunas));
  raiz.appendChild(grade);

  document.querySelectorAll("[data-aba]").forEach((b) => {
    const ativo = (b as HTMLElement).dataset.aba === atual;
    b.className = ativo
      ? "rounded-md bg-stone-900 px-3.5 py-2 text-sm font-medium text-white"
      : "rounded-md px-3.5 py-2 text-sm font-medium text-stone-600 hover:bg-stone-200";
  });
}

function iniciar(): void {
  const dados = window.DASHBOARD_DATA;
  if (!dados) {
    document.body.innerHTML =
      '<p class="p-8 text-red-700">data.js não carregou. Gere com: ' +
      "<code>uv run python -m churn_diag</code></p>";
    return;
  }
  const abas = document.getElementById("abas") as HTMLElement;
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
  const rodape = document.getElementById("rodape") as HTMLElement;
  rodape.textContent =
    `Snapshot ${dados.snapshot} · período-alvo a partir de ${dados.inicio_periodo_alvo} · ` +
    dados.aviso;
  render();
  let t: number;
  window.addEventListener("resize", () => {
    window.clearTimeout(t);
    t = window.setTimeout(render, 180);
  });
}

document.addEventListener("DOMContentLoaded", iniciar);
