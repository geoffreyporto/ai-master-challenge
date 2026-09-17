# Tasks: Classificador de tickets

> feature: classificador-tickets

<!-- Status: pendente | em-andamento | concluida. Refs e Arquivos verificados por onp-spec audit. -->

## T-003 — Split, B0 TF-IDF+LR, B1 Model2Vec+LR, calibração [concluida]
- Refs: US-004, AC-009, AC-010, AC-011, AC-012
- Arquivos: src/support_redesign/classifier.py, tests/test_classifier.py
- Notas: o analisador de n-gramas é próprio (não o regex do sklearn) para o Rust replicar byte a byte.

## T-004 — Adaptador Pioneer GLiNER2 (zero-shot) com cache [concluida]
- Refs: AC-011
- Arquivos: src/support_redesign/pioneer.py, tests/test_pioneer.py
- Notas: store=false; a API só devolve top-1 + confiança (top_k e multi_label=true retornam vazio); resultados em cache para o teste não chamar a API.

## T-013 — GLiNER2 multi-large com fallback e LLM como classificador [concluida]
- Refs: AC-030, AC-031
- Arquivos: src/support_redesign/pioneer.py, src/support_redesign/hosted.py, src/support_redesign/hosted_eval.py, tests/test_hosted.py, tests/test_pioneer.py
- Notas: cliente httpx com keep-alive; 429/503 respeitam Retry-After (cold start); cache por tarefa em outputs/pioneer/.
