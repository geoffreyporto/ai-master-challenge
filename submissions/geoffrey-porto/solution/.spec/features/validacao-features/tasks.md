# Tasks: Validação das features da referência

> feature: validacao-features

## T-011 — Features de taxa e lista de quarentena [concluida]
- Refs: AC-019, AC-024
- Arquivos: src/churn_diag/features.py, tests/test_features.py
- Notas: denominador zero devolve vazio (não zero); `QUARANTINED_UNDATED` declarado aqui e usado por risk.py e pelo painel de conta.

## T-012 — Painel por conta replicando o desenho da referência [concluida]
- Refs: AC-021, AC-022
- Arquivos: src/churn_diag/account_panel.py, tests/test_account_panel.py
- Notas: conta × fim de mês, janela de 90 dias, rótulo de evento de churn não-reativação em 30 dias, treino até 31/08/2024.

## T-013 — Triagem univariada e comparação de idades [concluida]
- Refs: AC-020, AC-023
- Arquivos: src/churn_diag/screening.py, tests/test_screening.py
- Notas: AUC + Holm por feature; idade da conta × idade da assinatura com correlação e modelos.

## T-014 — Quarentena aplicada ao diagnóstico e saídas no pipeline [concluida]
- Refs: AC-024, AC-020, AC-023
- Arquivos: src/churn_diag/risk.py, src/churn_diag/pipeline.py, tests/test_risk.py, outputs/feature_screening.csv, outputs/account_panel_metrics.csv, outputs/age_comparison.csv
- Notas: tirar as flags da matriz reestima logística e GBM — relatório e README acompanham (números conferidos por teste).

## T-015 — Documentar os resultados medidos [concluida]
- Refs: US-007, US-008, US-009
- Arquivos: ../docs/04-matriz-de-features.md, ../docs/referencia/README.md, RELATORIO.md, ../README.md
- Notas: atualizar a matriz com o que foi medido e registrar a replicação ao lado dos números da referência (ROC 0,604 · AP 0,144).
