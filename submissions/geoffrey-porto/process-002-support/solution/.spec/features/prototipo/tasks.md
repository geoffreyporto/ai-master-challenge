# Tasks: Protótipo funcional

> feature: prototipo

<!-- Status: pendente | em-andamento | concluida. Refs e Arquivos verificados por onp-spec audit. -->

## T-009 — Pipeline, métricas e exportação do modelo para o roteador [concluida]
- Refs: US-009, US-010, AC-028
- Arquivos: src/support_redesign/__init__.py, src/support_redesign/pipeline.py, src/support_redesign/__main__.py, src/support_redesign/export.py, tests/test_router.py
- Notas: gera outputs/metrics.json, outputs/router_model.json e o golden do hold-out.

## T-010 — Roteador Rust (axum 0.8, tokio) [concluida]
- Refs: US-010, AC-027, AC-028, AC-029
- Arquivos: router/Cargo.toml, router/rust-toolchain.toml, router/src/main.rs, router/src/lib.rs, router/src/model.rs, router/src/policy.rs, router/src/scores.rs, router/tests/api.rs, router/tests/parity.rs, router/clippy.toml
- Notas: pytest chama cargo test para que a prova entre no mesmo TAP.

## T-011 — App Streamlit [concluida]
- Refs: US-009, AC-025, AC-026
- Arquivos: app/streamlit_app.py, tests/test_app.py

## T-012 — README com números conferidos [concluida]
- Refs: US-009
- Arquivos: tests/test_readme_numbers.py, ../README.md
- Notas: P-003 — todo <!--m:chave--> do README bate com outputs/metrics.json.

## T-017 — Binários multiplataforma, lançador e início automático no app [concluida]
- Refs: US-013, AC-038, AC-039
- Arquivos: router/build-dist.sh, router/dist/SHA256SUMS, src/support_redesign/router_bin.py, tests/test_router_bin.py, tests/test_app.py, src/support_redesign/export.py
- Notas: modelo gzip compartilhado (router/dist/router_model.json.gz); Linux musl estático e Windows gnu compilados no container oficial rust:1.98.1.

## T-018 — Testes funcionais E2E com Playwright e capturas de tela [concluida]
- Refs: US-014, AC-040, AC-041
- Arquivos: tests/e2e/test_playwright_app.py
- Notas: usa o Chrome instalado (`channel="chrome"`); servidor Streamlit em porta livre; capturas em process-log/screenshots/.
