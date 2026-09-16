# Painéis de decisão (client-side)

Cinco painéis — CEO, Vendas, Marketing, Financeiro e Operações/CS — cada um com
os quatro níveis de análise: descritivo, diagnóstico, preditivo e prescritivo.

## Como abrir

```bash
open dashboard/index.html          # funciona direto, sem servidor e sem internet
```

Ou, se preferir servir:

```bash
python3 -m http.server 8777 --directory dashboard
```

## Como regenerar

```bash
uv run python -m churn_diag                 # recalcula tudo e reescreve data.js
tsc -p dashboard/tsconfig.json              # recompila src/*.ts em app.js
```

## O que tem dentro

| Arquivo | Papel |
|---|---|
| `index.html` | Casca da página: cabeçalho, abas, rodapé. Estilo em Tailwind + CSS3 próprio. |
| `src/tipos.ts` | Contrato do payload (o mesmo formato que `churn_diag.dashboards` grava). |
| `src/formato.ts` | Formatação pt-BR e a paleta do relatório — o painel não conta a história com outras cores. |
| `src/graficos.ts` | Gráficos D3: séries, barras, barras agrupadas e tabelas. |
| `src/app.ts` | Montagem dos painéis, abas e blocos de nível. |
| `app.js` | Saída do `tsc` — versionada para a página abrir sem build. |
| `data.js` | Payload gerado pelo pipeline Python. **Não editar à mão.** |
| `vendor/` | `d3` 7.9 e `tailwind` 3.4 vendorizados, para a página funcionar offline. |

## Duas decisões que valem explicação

**1. `data.js` é atribuição global, não `fetch`.** Um `fetch("data.json")` a
partir de `file://` esbarra em CORS e a página abriria vazia na máquina do
avaliador. Carregar como `<script>` resolve sem servidor.

**2. Lacuna declarada em vez de número estimado.** Todo painel termina com uma
seção "O que este painel NÃO mostra". CAC, LTV com margem, verba de mídia,
frequência de login e descontos não existem nas cinco tabelas do dataset —
então não aparecem como número em lugar nenhum. Isso é verificado por teste
(`tests/test_dashboards.py::test_kpi_impossivel_nao_vira_numero`): se alguém
adicionar um KPI de CAC ao painel, a suíte quebra.

Os KPIs que **têm** origem mostram a chave de onde vieram
(`metrics.json → mrr_churn_dec24_pct`), e o teste `test_todo_kpi_com_chave_bate_com_o_pipeline`
compara valor a valor com o pipeline recalculado.
