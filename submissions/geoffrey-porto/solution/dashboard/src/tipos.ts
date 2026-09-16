/** Formato do payload gerado por `churn_diag.dashboards` (data.js). */

type Direcao = "bom" | "ruim" | "neutro";

interface Kpi {
  rotulo: string;
  valor: number;
  unidade: string;
  nota: string;
  direcao: Direcao;
  chave: string;
}

interface Acao {
  acao: string;
  porque: string;
  confianca: "alta" | "media" | "baixa";
}

interface Lacuna {
  kpi: string;
  porque: string;
}

interface Linha {
  [coluna: string]: string | number | boolean | null;
}

interface Secao {
  titulo: string;
  grafico: string;
  dados: Linha[];
  leitura: string;
  confiabilidade?: string;
  acoes?: Acao[];
  limite_controle?: number;
  quebra?: { antes: number; depois: number; ic_depois: [number, number] };
}

interface Painel {
  titulo: string;
  publico: string;
  pergunta: string;
  kpis: Kpi[];
  descritivo: Secao;
  diagnostico: Secao;
  preditivo: Secao;
  prescritivo: Secao;
  lacunas: Lacuna[];
}

interface Payload {
  gerado_por: string;
  snapshot: string;
  inicio_periodo_alvo: string;
  aviso: string;
  paineis: { [nome: string]: Painel };
}

declare const Plotly: any;
declare const Chart: any;

interface Window {
  DASHBOARD_DATA: Payload;
}
