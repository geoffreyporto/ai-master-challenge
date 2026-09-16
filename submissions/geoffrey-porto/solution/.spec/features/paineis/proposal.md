# Proposal: paineis

## Why

O documento *Dashboards - Metrics and KPIs* pede cinco painéis (CEO, Vendas,
Marketing, Financeiro, Operações/CS), cada um com os quatro níveis de análise.
O diagnóstico já responde às perguntas; o que falta é a superfície onde cada
stakeholder vê a parte que lhe cabe e age.

Duas decisões governam esta feature:

1. **Nenhum número nasce na página.** O JSON do painel é gerado pelo mesmo
   pipeline que gera o relatório, e a taxa mensal delega a `monthly_churn` para
   não existir um segundo "churn de dezembro" (3,52% no relatório contra 6,75%
   se o denominador mudasse).
2. **KPI que o dataset não sustenta fica em branco, declarado.** CAC, LTV com
   margem, verba de mídia, logins e descontos não existem nas cinco tabelas.
   Cada painel lista suas lacunas — porque um painel executivo com número
   inventado é pior que um painel faltando número.

## What Changes

- `churn_diag.dashboards`: agregações por stakeholder + montagem do payload.
- `dashboard/`: página client-side (HTML + TypeScript compilado + Tailwind + D3),
  com `d3` e `tailwind` vendorizados para abrir sem internet.
- `python -m churn_diag` passa a gerar `dashboard/data.js` junto dos `outputs/`.

## Impact

- Não muda score, achado ou recomendação: é superfície de leitura.
- Acrescenta uma camada de apresentação que precisa ser regenerada junto com o
  pipeline — garantido por teste.
