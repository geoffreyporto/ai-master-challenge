# Tasks: Painéis por stakeholder

> feature: paineis

## T-028 — Agregações e payload dos cinco painéis [concluída]

- Refs: AC-044, AC-045, AC-046, AC-047
- Arquivos: src/churn_diag/dashboards.py, src/churn_diag/pipeline.py, tests/test_dashboards.py
- Notas: a série mensal delega a `monthly_churn` para não criar um segundo número de churn.

## T-029 — Página client-side (HTML + TypeScript + Tailwind + D3) [concluída]

- Refs: AC-044
- Arquivos: dashboard/index.html, dashboard/src/*.ts, dashboard/app.js, dashboard/vendor/, dashboard/README.md
- Notas: `tsc` compila `src/*.ts` em `app.js`; d3 e tailwind vendorizados; abre por file:// ou por servidor estático.
