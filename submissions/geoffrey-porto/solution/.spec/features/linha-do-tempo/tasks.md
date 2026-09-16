# Tasks: Features de linha do tempo e contrato de dados

> feature: linha-do-tempo

## T-021 — Features de linha do tempo nos dois recortes [concluida]
- Refs: AC-031
- Arquivos: src/churn_diag/features.py, tests/test_timeline.py
- Notas: razão de tendência com a fórmula da referência ((2ª metade + 1) ÷ (1ª metade + 1)); recorte consistente filtra uso dentro da janela da assinatura.

## T-022 — Bandeira, bloqueio e triagem [concluida]
- Refs: AC-032, AC-033
- Arquivos: src/churn_diag/account_panel.py, src/churn_diag/pipeline.py, tests/test_timeline.py, tests/test_reference_map.py
- Notas: `TIMELINE_UNRELIABLE` num lugar só; teste garante ausência no score e na replicação; registro ganha o status "medida sob bandeira".

## T-023 — Contrato de dados [concluida]
- Refs: AC-034
- Arquivos: ../docs/05-contrato-de-dados.md, tests/test_timeline.py, ../docs/04-matriz-de-features.md
- Notas: um item por linha bloqueada do registro, com campo faltante e teste de aceitação; teste de cobertura cruza contrato × registro.
