# Tasks: Explicabilidade como auditoria

> feature: explicabilidade

## T-026 — Valores de Shapley exatos e os gráficos globais [concluída]

- Refs: AC-040, AC-041
- Arquivos: src/churn_diag/explainability.py, tests/test_explainability.py
- Notas: enumeração de coalizões com função de valor intervencional; beeswarm, dependência, waterfall e heatmap por ambiente em matplotlib (mesma paleta das outras figuras).

## T-027 — Escada de CATE, explicação do score e relatório [concluída]

- Refs: AC-042, AC-043
- Arquivos: src/churn_diag/dml.py, src/churn_diag/pipeline.py, tests/test_explainability.py, RELATORIO.md, ../docs/07-perguntas-incomodas.md
- Notas: CATE por DR-learner com quantis formados no treino e médias no teste; waterfall exato do score de produção; seção no relatório.
