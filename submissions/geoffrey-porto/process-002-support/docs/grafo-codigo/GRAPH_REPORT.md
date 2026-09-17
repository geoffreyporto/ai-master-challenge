# Graph Report - solution  (2026-09-16)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 504 nodes · 951 edges · 27 communities
- Extraction: 98% EXTRACTED · 2% INFERRED · 0% AMBIGUOUS · INFERRED: 21 edges (avg confidence: 0.6)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Community 0
- Community 1
- Community 2
- Community 3
- Community 4
- Community 5
- Community 6
- Community 7
- Community 8
- Community 9
- Community 10
- Community 11
- Community 12
- Community 13
- Community 14
- Community 15
- Community 16
- Community 17
- Community 18
- Community 19
- Community 20
- Community 21
- Community 22
- Community 23
- Community 24
- Community 25
- Community 26

## God Nodes (most connected - your core abstractions)
1. `run()` - 38 edges
2. `PioneerClient` - 21 edges
3. `_run()` - 19 edges
4. `TfidfLR` - 16 edges
5. `RouterModel` - 15 edges
6. `FakeClient` - 15 edges
7. `diagnose()` - 13 edges
8. `route()` - 12 edges
9. `Decision` - 12 edges
10. `Policy` - 11 edges

## Surprising Connections (you probably didn't know these)
- `similar()` --calls--> `normalize()`  [INFERRED]
  solution/app/streamlit_app.py → solution/src/support_redesign/text.py
- `route()` --calls--> `decide()`  [INFERRED]
  solution/router/src/lib.rs → solution/router/src/policy.rs
- `HostedInputs` --uses--> `Decision`  [INFERRED]
  solution/src/support_redesign/hosted_eval.py → solution/src/support_redesign/boundary.py
- `LazyClient` --uses--> `Decision`  [INFERRED]
  solution/src/support_redesign/hosted_eval.py → solution/src/support_redesign/boundary.py
- `test_class_without_viable_threshold_is_human_only()` --calls--> `class_thresholds()`  [EXTRACTED]
  solution/tests/test_boundary.py → solution/src/support_redesign/boundary.py

## Import Cycles
- None detected.

## Communities (27 total, 0 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.07
Nodes (38): build_messages(), Draft, draft_reply(), draft_report(), Any, Rascunho de primeira resposta: máscara → LLM → guardrail (feature rascunho-…, classify(), classify_llm() (+30 more)

### Community 1 - "Community 1"
Cohesion: 0.07
Nodes (34): Config, Item, Parser, load_d1(), load_d2(), DataFrame, Path, Leitura dos dois datasets e split determinístico do Dataset 2. (+26 more)

### Community 2 - "Community 2"
Cohesion: 0.09
Nodes (31): analyzer(), ModelError, normalize(), RawModel, Error, HashMap, Path, Result (+23 more)

### Community 3 - "Community 3"
Cohesion: 0.10
Nodes (32): Body, Into, IntoResponse, Json, JsonRejection, Request, Response, Router (+24 more)

### Community 4 - "Community 4"
Cohesion: 0.10
Nodes (20): FileNotFoundError, DataDirNotFoundError, Path, Configuração única do projeto: caminhos, semente e parâmetros de decisão., Os CSVs não estão onde o pipeline espera., resolve_data_dir(), _band(), load_assumptions() (+12 more)

### Community 5 - "Community 5"
Cohesion: 0.13
Nodes (23): pick_production(), O modelo de produção sai da validação — nunca do teste (P-002)., B0: TF-IDF uni+bigramas (analisador próprio) + regressão logística., TfidfLR, export_dist_model(), export_golden(), export_router_model(), Decision (+15 more)

### Community 6 - "Community 6"
Cohesion: 0.15
Nodes (17): closed_with_hours(), csat_mde_between_channels(), diagnose(), Finding, kruskal(), ordinal_csat(), Any, DataFrame (+9 more)

### Community 7 - "Community 7"
Cohesion: 0.21
Nodes (19): class_thresholds(), conformal_qhat(), decide(), decide_all(), Decision, fit_policy(), human_examples(), Policy (+11 more)

### Community 8 - "Community 8"
Cohesion: 0.16
Nodes (12): chance_recall_at_k(), Any, ndarray, Índice de tickets similares e Recall@k (feature indice-resolucao)., Busca por cosseno sobre embeddings normalizados — só com o treino., Acerto esperado sorteando k vizinhos com a distribuição de classes do índice., recall_at_k(), SimilarIndex (+4 more)

### Community 9 - "Community 9"
Cohesion: 0.20
Nodes (16): Popen, binary_path(), checksums(), ensure_running(), health(), main(), NoBinaryError, platform_dir() (+8 more)

### Community 10 - "Community 10"
Cohesion: 0.15
Nodes (12): LogisticRegression, _logreg(), Fração dos n-gramas do texto que existem no vocabulário (guarda de domínio)., analyzer(), normalize(), Normalização e analisador de n-gramas compartilhados por treino, app e…, Minúsculas, sem {placeholders}, só letras ASCII a-z separadas por um espaço., Unigramas e bigramas sobre os tokens normalizados. (+4 more)

### Community 11 - "Community 11"
Cohesion: 0.20
Nodes (10): Protocol, evaluate(), expected_calibration_error(), label_index(), Model2VecLR, ProbaClassifier, Any, ndarray (+2 more)

### Community 12 - "Community 12"
Cohesion: 0.24
Nodes (13): audit_d1(), audit_d2(), _chi2_uniform_p(), _closed_intervals_hours(), Any, DataFrame, Series, Auditoria de autenticidade dos dois datasets (feature auditoria-dados). (+5 more)

### Community 13 - "Community 13"
Cohesion: 0.24
Nodes (13): call_rust(), load_index(), load_metrics(), load_production(), load_tables(), Any, DataFrame, ndarray (+5 more)

### Community 14 - "Community 14"
Cohesion: 0.15
Nodes (10): Redesign de Suporte — G4 AI Master Challenge 002., free_addr(), Porta livre escolhida pelo sistema, para o teste não colidir com nada., fixture, Binários prontos: o avaliador roda o roteador sem Rust instalado., @spec:AC-038 @principle:P-005, @spec:AC-038 @principle:P-005, served() (+2 more)

### Community 15 - "Community 15"
Cohesion: 0.14
Nodes (11): Privacidade: máscara antes do LLM, guardrail depois., @spec:AC-033 @principle:P-012, @spec:AC-033 @principle:P-006, @spec:AC-034 @principle:P-013, @spec:AC-034 @principle:P-013, @spec:AC-035 @principle:P-012, test_guardrail_blocks_pii_and_passes_clean_text(), test_mask_replaces_pii_with_typed_placeholders() (+3 more)

### Community 16 - "Community 16"
Cohesion: 0.17
Nodes (12): _policy(), Fronteira: automatizar só onde o erro é raro, e nunca tudo., @spec:AC-013 @principle:P-002, @spec:AC-014 @principle:P-004, @spec:AC-015 @principle:P-004, @spec:AC-015 @principle:P-004, test_class_without_viable_threshold_is_human_only(), test_conformal_sets_keep_their_promise() (+4 more)

### Community 17 - "Community 17"
Cohesion: 0.20
Nodes (8): CompletedProcess, _cargo(), cargo_tests(), fixture, Roteador Rust: a prova do cargo entra no mesmo TAP do onp-spec., @spec:AC-028 @principle:P-005, test_router_passes_strict_lints(), test_rust_decides_like_python_on_full_holdout()

### Community 18 - "Community 18"
Cohesion: 0.27
Nodes (10): Box, arg_value(), main(), model_candidates(), Error, Option, PathBuf, Result (+2 more)

### Community 19 - "Community 19"
Cohesion: 0.31
Nodes (9): domain_shift(), Any, DataFrame, Decision, ndarray, Series, Cruzamento: o classificador do Dataset 2 aplicado ao Dataset 1 (cruzamento-…, score_d1() (+1 more)

### Community 20 - "Community 20"
Cohesion: 0.38
Nodes (7): HostedInputs, LazyClient, Any, Path, Avaliação dos modelos hospedados no Pioneer, com cache em outputs/pioneer/. O…, _run(), run_hosted()

### Community 21 - "Community 21"
Cohesion: 0.20
Nodes (9): Rascunho: sempre sugestão, nunca envio, sem vazar PII., @spec:AC-036 @principle:P-004 @principle:P-012, @spec:AC-036 @principle:P-013, @spec:AC-036 @principle:P-004, @spec:AC-037 @principle:P-013, test_draft_is_a_suggestion_with_context(), test_draft_with_pii_is_flagged(), test_no_code_path_sends_to_customer() (+1 more)

### Community 22 - "Community 22"
Cohesion: 0.22
Nodes (6): AppTest, app(), fixture, App: abre com dado real e a demo não escolhe a dedo., @spec:AC-026 @principle:P-004, test_demo_draws_a_holdout_ticket_and_shows_the_decision()

### Community 23 - "Community 23"
Cohesion: 0.28
Nodes (5): PioneerUnavailableError, Modelo não respondeu depois das retentativas., FakeClient, Any, Cliente Pioneer falso para testar comportamento sem rede.

### Community 24 - "Community 24"
Cohesion: 0.22
Nodes (5): Classificação hospedada: modelos definidos pelo dono, fallback e medição…, @spec:AC-030 @principle:P-012, @spec:AC-031 @principle:P-006, test_llm_measured_on_seeded_stratified_sample(), test_primary_model_serves_and_fallback_takes_over()

### Community 25 - "Community 25"
Cohesion: 0.28
Nodes (8): _d(), Decision, Segunda opinião: só entra se a validação provar a precisão., @spec:AC-032 @principle:P-004, @spec:AC-032 @principle:P-002, test_only_uncertainty_cases_are_eligible(), test_rule_is_enabled_only_with_validated_precision(), test_second_opinion_reported_on_validation_and_test()

### Community 26 - "Community 26"
Cohesion: 0.32
Nodes (4): _client(), Transporte Pioneer: a chave nunca vaza e o 503 de aquecimento é tratado., test_cold_start_503_is_retried_then_succeeds(), test_persistent_503_raises_unavailable()

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `run()` connect `Community 5` to `Community 1`, `Community 4`, `Community 6`, `Community 7`, `Community 8`, `Community 11`, `Community 12`, `Community 19`, `Community 20`?**
  _High betweenness centrality (0.132) - this node is a cross-community bridge._
- **Why does `route()` connect `Community 3` to `Community 2`?**
  _High betweenness centrality (0.127) - this node is a cross-community bridge._
- **Why does `RouterModel` connect `Community 3` to `Community 2`?**
  _High betweenness centrality (0.104) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `run()` (e.g. with `.similar()` and `metrics()`) actually correct?**
  _`run()` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 4 inferred relationships involving `PioneerClient` (e.g. with `Draft` and `HostedInputs`) actually correct?**
  _`PioneerClient` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `TfidfLR` (e.g. with `HostedInputs` and `LazyClient`) actually correct?**
  _`TfidfLR` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.06857142857142857 - nodes in this community are weakly interconnected._