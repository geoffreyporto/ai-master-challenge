# Tasks: Features derivadas da referência

> feature: derivadas-features

## T-018 — Fórmulas das duas derivadas [concluida]
- Refs: AC-027, AC-028
- Arquivos: src/churn_diag/features.py, tests/test_derived.py
- Notas: z-scores recebem os parâmetros de fora (ajustados no treino); vazio em bloco quando não há ticket.

## T-019 — Derivadas no painel, na triagem e no registro [concluida]
- Refs: AC-029
- Arquivos: src/churn_diag/account_panel.py, src/churn_diag/pipeline.py, tests/test_screening.py, ../docs/04-matriz-de-features.md
- Notas: fora da replicação da referência e do score de produção; registro passa de ⬜ para ✅.

## T-020 — Decomposição das derivadas com sinal [concluida]
- Refs: AC-030
- Arquivos: src/churn_diag/screening.py, tests/test_screening.py, src/churn_diag/pipeline.py
- Notas: regra permanente — composta significativa só vira achado depois de mostrar se o sinal é do numerador ou do denominador.
