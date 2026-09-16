/** Gráficos interativos: Plotly.js para as duas séries (zoom, pan, hover
 *  unificado, exportação nativa em PNG) e Chart.js para barras e barras
 *  agrupadas (tooltip, legenda clicável, responsivo).
 *
 *  Regra de projeto herdada da versão em D3: nenhum gráfico inventa escala
 *  nem esconde zero. Barra começa em zero; série temporal mostra o eixo
 *  inteiro; barra de erro aparece sempre que o payload traz erro-padrão.
 *  Gráfico que engana é pior que tabela.
 */

interface OpcoesBarra {
  campoX: string;
  campoY: string;
  rotuloY: string;
  formatador?: (v: number) => string;
  cor?: string;
  horizontal?: boolean;
}

const FONTE = "ui-sans-serif, system-ui, -apple-system, sans-serif";

/** Cada canvas/div de gráfico guarda a instância que o criou, para destruir
 *  antes de redesenhar — sem isso, redimensionar a janela vaza um Chart por
 *  resize. */
function limpar(alvo: HTMLElement): void {
  const existente = (alvo as { _chart?: { destroy(): void } })._chart;
  if (existente) existente.destroy();
  alvo.innerHTML = "";
}

function novoCanvas(alvo: HTMLElement, altura: number): HTMLCanvasElement {
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

function novoDiv(alvo: HTMLElement, altura: number): HTMLDivElement {
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
function barras(alvo: HTMLElement, dados: Linha[], op: OpcoesBarra): void {
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
            label: (ctx: { parsed: { x: number; y: number } }) =>
              fmt(op.horizontal ? ctx.parsed.x : ctx.parsed.y),
          },
        },
      },
      scales: {
        x: op.horizontal
          ? {
              beginAtZero: true,
              ticks: { font: { family: FONTE, size: 10 }, callback: (v: number) => fmt(v) },
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
              ticks: { font: { family: FONTE, size: 10 }, callback: (v: number) => fmt(v) },
              grid: { color: PALETA.grade },
            },
      },
    },
  });
  (alvo as { _chart?: unknown })._chart = chart;
}

/** 3. Barras agrupadas: risco por faixa de idade, referência × período-alvo.
 *  Clicar num item da legenda esconde/mostra o período inteiro — útil para
 *  isolar visualmente o efeito da quebra de regime. */
function risco(alvo: HTMLElement, dados: Linha[]): void {
  const rotuloPeriodo: { [k: string]: string } = {
    reference: "jan–set/24",
    target: "out–dez/24",
  };
  const faixas = Array.from(new Set(dados.map((d) => String(d["age_bucket"]))));
  const canvas = novoCanvas(alvo, 300);

  const serie = (periodo: string, cor: string) => ({
    label: rotuloPeriodo[periodo],
    data: faixas.map((faixa) => {
      const linha = dados.find(
        (d) => d["age_bucket"] === faixa && d["period"] === periodo
      );
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
          callbacks: { label: (ctx: any) => `${ctx.dataset.label}: ${br(ctx.parsed.y, 2)}%` },
        },
      },
      scales: {
        x: { ticks: { font: { family: FONTE, size: 10 } }, grid: { display: false } },
        y: {
          beginAtZero: true,
          title: { display: true, text: "risco mensal (%)", font: { family: FONTE, size: 10 } },
          ticks: {
            font: { family: FONTE, size: 10 },
            callback: (v: number) => br(v, 1) + "%",
          },
          grid: { color: PALETA.grade },
        },
      },
    },
  });
  (alvo as { _chart?: unknown })._chart = chart;
}

/** 4. Série mensal: barras de MRR perdido + linha da taxa de churn no eixo
 *  secundário, com o limite de controle marcado. Plotly dá zoom por arraste,
 *  pan, reset e hover unificado nas duas séries ao mesmo tempo — o ponto
 *  onde a quebra de regime aparece fica exploratório, não só ilustrado. */
function serieChurn(alvo: HTMLElement, dados: Linha[], ucl?: number): void {
  const pontos = dados.filter((d) => String(d["month"]) >= "2024-01-01");
  const div = novoDiv(alvo, 340);
  const meses = pontos.map((d) => mesCurto(String(d["month"])));
  const mrrPerdido = pontos.map((d) => Number(d["churned_mrr"]));
  const taxaChurn = pontos.map((d) => Number(d["mrr_churn_pct"]));

  const tracos: any[] = [
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

  const shapes: any[] = [];
  const anotacoes: any[] = [];
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

  Plotly.newPlot(
    div,
    tracos,
    {
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
    },
    {
      responsive: true,
      displaylogo: false,
      modeBarButtonsToRemove: ["lasso2d", "select2d", "autoScale2d"],
    }
  );
  (alvo as { _chart?: unknown })._chart = { destroy: () => Plotly.purge(div) };
}

/** Tabela — quando a leitura correta é linha a linha, não barra.
 *  Interatividade: clicar num cabeçalho ordena por aquela coluna (numérica
 *  ou texto), clicar de novo inverte — sem nenhuma dependência extra. */
function tabela(
  alvo: HTMLElement,
  dadosOriginais: Linha[],
  colunas: string[],
  titulos: string[]
): void {
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
        const cmp =
          typeof va === "number" && typeof vb === "number"
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

  function desenharCorpo(): void {
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
