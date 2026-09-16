# Tasks: Completude do mapa de features

> feature: completude-features

## T-016 — Registro das features da referência [concluida]
- Refs: AC-025
- Arquivos: src/churn_diag/features.py, tests/test_reference_map.py
- Notas: dados puros em `features.py` (sem importar os painéis, para não criar ciclo); o cruzamento com as colunas reais é feito no teste.

## T-017 — Tabelas do documento alinhadas ao registro [concluida]
- Refs: AC-026
- Arquivos: ../docs/04-matriz-de-features.md, tests/test_reference_map.py
- Notas: legenda nova (implementada / quarentena / excluída) e contagem conferida por teste.
