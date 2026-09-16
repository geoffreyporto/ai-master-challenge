/** Gráficos D3 — um por tipo declarado no payload.
 *
 *  Regra de projeto: nenhum gráfico inventa escala nem esconde zero. Barra
 *  começa em zero; série temporal mostra o eixo inteiro; barra de erro aparece
 *  sempre que o payload traz erro-padrão. Gráfico que engana é pior que tabela.
 */

interface OpcoesBarra {
  campoX: string;
  campoY: string;
  rotuloY: string;
  formatador?: (v: number) => string;
  cor?: string;
  horizontal?: boolean;
}

const MARGEM = { topo: 16, direita: 18, baixo: 44, esquerda: 64 };

function svgBase(alvo: HTMLElement, altura: number): any {
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

function eixoY(g: any, escala: any, largura: number, rotulo: string): void {
  g.append("g")
    .call(d3.axisLeft(escala).ticks(5).tickSize(-largura))
    .call((sel: any) => sel.select(".domain").remove())
    .call((sel: any) =>
      sel.selectAll(".tick line").attr("stroke", PALETA.grade)
    )
    .call((sel: any) =>
      sel.selectAll("text").attr("fill", PALETA.tinta2).attr("font-size", 11)
    );
  g.append("text")
    .attr("transform", "rotate(-90)")
    .attr("y", -MARGEM.esquerda + 14)
    .attr("x", -10)
    .attr("fill", PALETA.tinta2)
    .attr("font-size", 11)
    .attr("text-anchor", "end")
    .text(rotulo);
}

function barras(alvo: HTMLElement, dados: Linha[], op: OpcoesBarra): void {
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
      .call((s: any) => s.selectAll("text").attr("fill", PALETA.tinta2).attr("font-size", 11));
    g.append("g")
      .call(d3.axisLeft(y).tickSize(0))
      .call((s: any) => s.select(".domain").remove())
      .call((s: any) => s.selectAll("text").attr("fill", PALETA.tinta2).attr("font-size", 11));
    g.selectAll("rect")
      .data(dados)
      .join("rect")
      .attr("y", (d: Linha) => y(String(d[op.campoX])))
      .attr("x", (d: Linha) => x(Math.min(0, Number(d[op.campoY]))))
      .attr("height", y.bandwidth())
      .attr("width", (d: Linha) =>
        Math.abs(x(Number(d[op.campoY])) - x(0))
      )
      .attr("fill", (d: Linha) =>
        Number(d[op.campoY]) < 0 ? PALETA.laranja : op.cor || PALETA.azul
      )
      .attr("rx", 2);
    g.selectAll("text.valor")
      .data(dados)
      .join("text")
      .attr("class", "valor")
      .attr("y", (d: Linha) => y(String(d[op.campoX])) + y.bandwidth() / 2 + 4)
      .attr("x", (d: Linha) => x(Number(d[op.campoY])) + 6)
      .attr("fill", PALETA.tinta2)
      .attr("font-size", 11)
      .text((d: Linha) => fmt(Number(d[op.campoY])));
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
    .call((s: any) => s.select(".domain").attr("stroke", PALETA.grade))
    .call((s: any) =>
      s
        .selectAll("text")
        .attr("fill", PALETA.tinta2)
        .attr("font-size", 11)
        .attr("transform", dados.length > 6 ? "rotate(-20)" : null)
        .attr("text-anchor", dados.length > 6 ? "end" : "middle")
    );
  g.selectAll("rect")
    .data(dados)
    .join("rect")
    .attr("x", (d: Linha) => x(String(d[op.campoX])))
    .attr("y", (d: Linha) => y(Math.max(0, Number(d[op.campoY]))))
    .attr("width", x.bandwidth())
    .attr("height", (d: Linha) => Math.abs(y(Number(d[op.campoY])) - y(0)))
    .attr("fill", (d: Linha) =>
      Number(d[op.campoY]) < 0 ? PALETA.laranja : op.cor || PALETA.azul
    )
    .attr("rx", 2);
  g.selectAll("text.valor")
    .data(dados)
    .join("text")
    .attr("class", "valor")
    .attr("x", (d: Linha) => x(String(d[op.campoX])) + x.bandwidth() / 2)
    .attr("y", (d: Linha) => y(Number(d[op.campoY])) - 6)
    .attr("text-anchor", "middle")
    .attr("fill", PALETA.tinta2)
    .attr("font-size", 11)
    .text((d: Linha) => fmt(Number(d[op.campoY])));
}

/** Série mensal: barras de MRR perdido + linha da taxa, com limite de controle. */
function serieChurn(alvo: HTMLElement, dados: Linha[], ucl?: number): void {
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
    .domain([0, d3.max(pontos, (d: Linha) => Number(d["churned_mrr"])) * 1.15])
    .range([h, 0]);
  const yTaxa = d3
    .scaleLinear()
    .domain([0, d3.max(pontos, (d: Linha) => Number(d["mrr_churn_pct"])) * 1.3])
    .range([h, 0]);

  eixoY(g, yMrr, w, "MRR perdido (US$)");
  g.append("g")
    .attr("transform", `translate(${w},0)`)
    .call(d3.axisRight(yTaxa).ticks(5).tickFormat((v: number) => br(v, 1) + "%"))
    .call((s: any) => s.select(".domain").remove())
    .call((s: any) =>
      s.selectAll("text").attr("fill", PALETA.laranja).attr("font-size", 11)
    );
  g.append("g")
    .attr("transform", `translate(0,${h})`)
    .call(d3.axisBottom(x).tickFormat((v: string) => mesCurto(v)))
    .call((s: any) => s.select(".domain").attr("stroke", PALETA.grade))
    .call((s: any) =>
      s.selectAll("text").attr("fill", PALETA.tinta2).attr("font-size", 11)
    );

  g.selectAll("rect")
    .data(pontos)
    .join("rect")
    .attr("x", (d: Linha) => x(String(d["month"])))
    .attr("y", (d: Linha) => yMrr(Number(d["churned_mrr"])))
    .attr("width", x.bandwidth())
    .attr("height", (d: Linha) => h - yMrr(Number(d["churned_mrr"])))
    .attr("fill", PALETA.azul)
    .attr("opacity", 0.85)
    .attr("rx", 2);

  const linha = d3
    .line()
    .x((d: Linha) => x(String(d["month"])) + x.bandwidth() / 2)
    .y((d: Linha) => yTaxa(Number(d["mrr_churn_pct"])));
  g.append("path")
    .datum(pontos)
    .attr("fill", "none")
    .attr("stroke", PALETA.laranja)
    .attr("stroke-width", 2.4)
    .attr("d", linha);
  g.selectAll("circle")
    .data(pontos)
    .join("circle")
    .attr("cx", (d: Linha) => x(String(d["month"])) + x.bandwidth() / 2)
    .attr("cy", (d: Linha) => yTaxa(Number(d["mrr_churn_pct"])))
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
function risco(alvo: HTMLElement, dados: Linha[]): void {
  const periodos = ["reference", "target"];
  const rotulo: { [k: string]: string } = {
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
    .domain([0, d3.max(dados, (d: Linha) => Number(d["hazard_pct"])) * 1.2])
    .range([h, 0]);

  eixoY(g, y, w, "risco mensal (%)");
  g.append("g")
    .attr("transform", `translate(0,${h})`)
    .call(d3.axisBottom(x0).tickSize(0))
    .call((s: any) => s.select(".domain").attr("stroke", PALETA.grade))
    .call((s: any) =>
      s.selectAll("text").attr("fill", PALETA.tinta2).attr("font-size", 11)
    );

  g.selectAll("rect")
    .data(dados.filter((d) => periodos.indexOf(String(d["period"])) >= 0))
    .join("rect")
    .attr("x", (d: Linha) => x0(String(d["age_bucket"])) + x1(String(d["period"])))
    .attr("y", (d: Linha) => y(Number(d["hazard_pct"])))
    .attr("width", x1.bandwidth())
    .attr("height", (d: Linha) => h - y(Number(d["hazard_pct"])))
    .attr("fill", (d: Linha) =>
      d["period"] === "target" ? PALETA.laranja : PALETA.azul
    )
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
function tabela(alvo: HTMLElement, dados: Linha[], colunas: string[], titulos: string[]): void {
  d3.select(alvo).selectAll("*").remove();
  const t = d3.select(alvo).append("table").attr("class", "w-full text-sm");
  t.append("thead")
    .append("tr")
    .attr("class", "text-left text-xs uppercase tracking-wide text-stone-500")
    .selectAll("th")
    .data(titulos)
    .join("th")
    .attr("class", "py-2 pr-3 font-semibold border-b border-stone-200")
    .text((d: string) => d);
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
      .text((d: Linha) => {
        const v = d[c];
        return typeof v === "number" ? brAuto(v) : String(v ?? "—");
      });
  });
}
