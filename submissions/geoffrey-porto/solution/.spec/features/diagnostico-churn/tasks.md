# Tasks: Diagnóstico de churn da RavenStack

> feature: diagnostico-churn

<!--
  T-xxx = tarefa. `Refs:` = histórias/critérios atendidos. `Arquivos:` decide o
  que o `onp-spec plano` pode rodar em paralelo (arquivos disjuntos).
  Uma tarefa só vira [concluida] com prova PASS dos seus critérios (verify).
  1 tarefa = 1 commit atômico: `T-00X diagnostico-churn: <título>`.
-->

## T-001 — Esqueleto do projeto, configuração e emissor TAP [concluida]
- Refs: US-006
- Arquivos: pyproject.toml, src/churn_diag/__init__.py, src/churn_diag/config.py, tests/conftest.py, tests/fixtures.py
- Notas: Python 3.14 + Polars; ruff (I,F,E,W,PL,PT); pytest com emissor TAP próprio (título do teste traz `@spec:AC-xxx` da docstring) — zero dependência extra para o onp-spec ler a prova.

## T-002 — Carga das cinco tabelas com contrato de schema [concluida]
- Refs: AC-001
- Arquivos: src/churn_diag/loader.py, tests/test_loader.py
- Notas: `Tables` imutável; erro nomeia tabela e coluna.

## T-003 — Auditoria de qualidade e concordância das definições de churn [concluida]
- Refs: AC-002, AC-003, AC-004
- Arquivos: src/churn_diag/quality.py, tests/test_quality.py
- Notas: `usage_id` colide (IDs de 6 hex) — deduplicar só linha idêntica.

## T-004 — Métricas de churn: taxa, risco por idade, padronização, controle [concluida]
- Refs: AC-005, AC-006, AC-007
- Arquivos: src/churn_diag/metrics.py, tests/test_metrics.py
- Notas: painel assinatura×mês é a base de DRY para T-005, T-006 e T-007.

## T-005 — Registro de hipóteses, Holm, rótulos e invariância [concluida]
- Refs: AC-008, AC-009, AC-010, AC-011
- Arquivos: src/churn_diag/hypotheses.py, tests/test_hypotheses.py
- Notas: depende de T-004 (painel). Hipóteses H1–H12 (inclui as contradições CS/Produto e 4 cortes firmográficos).

## T-006 — Score de perda esperada, lista do CS e validação fora do tempo [concluida]
- Refs: AC-012, AC-013, AC-014
- Arquivos: src/churn_diag/risk.py, tests/test_risk.py
- Notas: depende de T-004. Benchmarks logística/GBM com todas as tabelas.

## T-007 — Impacto em MRR e tamanho de amostra do teste A/B [concluida]
- Refs: AC-015, AC-016
- Arquivos: src/churn_diag/impact.py, tests/test_impact.py
- Notas: depende de T-004.

## T-008 — Pipeline, figuras e reprodutibilidade [concluida]
- Refs: AC-017
- Arquivos: src/churn_diag/pipeline.py, src/churn_diag/figures.py, src/churn_diag/__main__.py, tests/test_pipeline.py
- Notas: depende de T-002..T-007. Saída determinística (ordenação estável, floats arredondados, PNG sem metadados de data).

## T-009 — Relatório do CEO com números rastreáveis [concluida]
- Refs: AC-018
- Arquivos: RELATORIO.md, tests/test_report.py
- Notas: depende de T-008. Cada número marcado `<!--m:chave-->` é conferido contra `outputs/metrics.json`.

## T-010 — Notebook narrativo (apêndice técnico) [concluida]
- Refs: US-003
- Arquivos: notebooks/diagnostico_churn.ipynb
- Notas: importa o pacote (DRY) — o notebook explica, não reimplementa.
