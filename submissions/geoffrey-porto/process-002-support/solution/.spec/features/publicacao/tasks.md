# Tasks: Publicação

> feature: publicacao

## T-019 — Demo pública e bootstrap do app [pendente]

- Refs: US-015, AC-042, AC-043
- Arquivos: app/streamlit_app.py, app/requirements.txt, src/support_redesign/bootstrap.py, tests/test_publicacao.py

## T-020 — API Rust na Vercel e página estática [pendente]

- Refs: US-015, AC-044, AC-045
- Arquivos: router/api/route.rs, router/vercel.json, router/.vercelignore, router/public/index.html, router/public/data.json, router/tests/vercel_api.rs, src/support_redesign/public_page.py
- Notas: runtime Rust oficial da Vercel (beta) com VercelLayer; modelo embutido via include_bytes.
