# Tasks: Efeito causal com Double Machine Learning

> feature: efeito-causal-dml

## T-024 — Estimador DML com agrupamento e sobreposição [concluida]
- Refs: AC-035, AC-036, AC-037, AC-038, AC-039
- Arquivos: src/churn_diag/dml.py, src/churn_diag/screening.py, tests/test_dml.py
- Notas: `GroupKFold` por conta; erro-padrão sanduíche agrupado; aparo em [0,02; 0,98]; efeito mínimo detectável a partir do erro-padrão agrupado.

## T-025 — Os dois casos de uso no pipeline e na documentação [concluida]
- Refs: AC-038, AC-039
- Arquivos: src/churn_diag/pipeline.py, tests/test_dml.py, ../docs/06-casos-dml.md, outputs/dml_use_cases.csv
- Notas: caso 1 escalação (só linhas com ticket), caso 2 cobrança anual; publicar poder junto.
