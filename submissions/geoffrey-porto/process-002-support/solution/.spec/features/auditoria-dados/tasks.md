# Tasks: Auditoria de autenticidade dos dados

> feature: auditoria-dados

<!-- Status: pendente | em-andamento | concluida. Refs e Arquivos verificados por onp-spec audit. -->

## T-001 — Configuração, leitura, normalização e auditoria [concluida]
- Refs: US-001, AC-001, AC-002, AC-003
- Arquivos: src/support_redesign/config.py, src/support_redesign/io.py, src/support_redesign/text.py, src/support_redesign/audit.py, tests/conftest.py, tests/test_audit.py, tests/test_text.py
- Notas: a contagem de placeholders usa um regex declarado em código (o valor depende dele).
