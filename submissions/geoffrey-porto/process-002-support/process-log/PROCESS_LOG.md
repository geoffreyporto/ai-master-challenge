# Process log — Challenge 002

Sessão única com Claude Code (Opus 5 a partir da fase de especificação; Sonnet 5
no setup), em 2026-09-16. Linha do tempo aproximada, decisões e erros pegos.

## Linha do tempo

| Hora (aprox.) | Etapa | O que a IA fez | O que eu decidi / corrigi |
|---|---|---|---|
| 0:00 | Regras | Leu README, CONTRIBUTING, guia de submissão, template | Notei "um PR por pessoa": o 002 vai no mesmo PR do 001 (decisão minha) |
| 0:05 | Dados | Baixou os dois datasets com Kaggle CLI | A IA foi bloqueada ao tentar ler o arquivo de credencial; usei cópia temporária e apaguei depois |
| 0:10 | Referências | Leu CRISP-DM, guia analítico, stack GLiNER2, metodologia SDD, padrões (SOLID, Rust standards) | — |
| 0:20 | Verificação | Re-mediu as afirmações dos docs no arquivo | Divergências viraram critério de aceite (AC-003) |
| 0:30 | Pioneer | Smoke test do catálogo e da inferência | Descobrimos que o schema dos docs retorna vazio e que não há GLiFormer nem upload por API |
| 0:40 | SDD | Constituição (P-001…P-011), 8 features, 29 AC, perguntas Q-001…Q-003 | Perguntas de negócio ficam **abertas** com dono e decisão na ausência |
| 1:00 | Docs | Plano de trabalho, guia de implementação, arquitetura e padrões | Cortei Erlang C, cleanlab e MAPIE (YAGNI); conformal em ~15 linhas |
| 1:10 | Pipeline | Auditoria, diagnóstico, B0/B1, fronteira, similares, cruzamento, ROI | Analisador de n-gramas próprio para o Rust replicar |
| 1:40 | Achado | Primeira execução: 18,4% dos tickets do Dataset 1 roteados automaticamente | Pedi investigação: fração de n-gramas conhecidos separa os domínios (0,84 × 0,58) → guarda de domínio no 2º percentil da validação. Resultado: 3,7% |
| 1:50 | Rust | Roteador axum 0.8.9 / Rust 1.98.1, paridade no hold-out | Exigi paridade em 100% dos tickets, não amostra: Δp máx 8,9e-16 |
| 2:10 | Testes | Suite pytest com tags `@spec`/`@principle`; pytest chama `cargo test` e `clippy` | — |
| 2:20 | App | Streamlit com 5 abas | Demo sorteia do hold-out (critério do challenge) |
| 2:30 | README | Números marcados `<!--m:chave-->` conferidos por teste | Mantive o ROI modesto e descontado de retrabalho |
| 2:40 | Pioneer (pedido do autor) | Troquei o benchmark para `gliner2-multi-large-v1` + fallback `gliner2-large-v1`; novas features `privacidade-guardrails` e `rascunho-resposta` (AC-030…AC-037, P-012, P-013) | Defini os papéis: GLiNER2 = benchmark e segunda opinião; privacy-filter = máscara antes do LLM; DeepSeek = rascunho + benchmark; gliguard = guardrail na saída |
| 2:55 | Cliente Pioneer | Troca de urllib por httpx com keep-alive e retentativa em 503 (aquecimento) | ~4 s → ~1 s por chamada |
| 3:10 | Abstenção | 3.327 tickets sem rótulo do multi-large (`topic_group: null`) | Abstenção passa a acionar o fallback; re-rodei só esses tickets |
| 3:15 | Guardrail | Aprovação dos rascunhos: 0% → 16,7% → 56,7% → 96,7% | Placeholder próprio ignorado; prompt sem cargos; pronomes ignorados. Não baixei o limiar |
| 3:20 | Decisão | Segunda opinião: 69,8% de precisão na validação | Regra desligada — teria criado retrabalho |
| 3:40 | Autonomia do avaliador (pedido do autor) | Binários do roteador para 5 plataformas + lançador Python + início automático no app | Linux/macOS executados; Windows só compilado |
| 4:00 | Arquitetura | Diagrama Archify validado (0 erros, 0 avisos) e checado em navegador | GLiNER2 ficou num cartão, fora do caminho de execução |
| 4:10 | Grafo do código | graphify achou ciclo de import `model.rs ↔ policy.rs` | Movi `Scores` para `scores.rs`; binários recompilados; grafo sem ciclos |
| 4:20 | E2E | 8 testes Playwright no Chrome real, com capturas | O rascunho real do Pioneer apareceu mascarado e aprovado pelo guardrail |
| 4:30 | Evidência | Export da sessão | Chave e e-mail redigidos antes de salvar; zip original substituído pela versão redigida |
| 5:00 | Publicação (pedido do autor) | Vercel: página estática + função Rust (runtime oficial, beta) com o modelo embutido; Streamlit Cloud com rascunho desligado | Rascunho público desligado: a chave é do autor |
| 5:20 | Falha no Streamlit Cloud | O app treinava tudo no boot; no Linux as probabilidades mudam na 9ª casa, o cache hospedado ficava incompleto e o pipeline tentava chamar o Pioneer sem chave | Pipeline só usa rede com `--pioneer`; o app serve o `router_model.json.gz` versionado (paridade testada) e só monta o índice no boot |
| 5:30 | Segfault | `pyarrow` 25.0.1 caía num container limpo (mesmo aviso do Streamlit Cloud) | `pyarrow<25` fixado |
| 5:40 | Regra do challenge | O Streamlit Cloud criou `.devcontainer/` na raiz do repositório em nome do autor | Removido num commit próprio; o PR só altera `submissions/geoffrey-porto/` |

## Decisões (contexto → escolha → evidência)

| # | Decisão | Evidência |
|---|---|---|
| D-01 | Dataset 1 é tratado como sintético e o diagnóstico vira auditoria + resultado nulo com poder | 100% placeholders, χ² p ≥ 0,11, 49,3% intervalos negativos, MDE 0,21 |
| D-02 | Modelo de produção = B0 TF-IDF+LR | Macro-F1 na **validação**: B0 0,861 × B1 0,747 |
| D-03 | Precisão-alvo 95% por fila, α = 5% | Suposição ASM-004 (Q-002 aberta) |
| D-04 | `Miscellaneous` só humano | ASM-005; fila de sobra |
| D-05 | Guarda de domínio (fração de n-gramas conhecidos ≥ 2º percentil da validação) | Dataset 1: 18,4% → 3,7% automático; Dataset 2: cobertura 59,9% → 58,9% |
| D-06 | Rust só serve B0 (JSON exportado), sem ONNX | KISS; paridade exata testada |
| D-07 | GLiNER2 (multi-large + fallback) e DeepSeek não roteiam | Macro-F1 0,288 (hold-out inteiro) e 0,392 (amostra de 400) contra 0,867/0,888 do B0 |
| D-09 | Segunda opinião do GLiNER2 desligada | Precisão das concordâncias na validação 69,8% < 95% |
| D-10 | Modelos hospedados entram no rascunho assistido | Máscara com recall 100% (n=200); 0 vazamentos e 96,7% de aprovação do guardrail (n=30) |
| D-11 | Base GLiNER2 (`gliner2-base-v1`) descartado a pedido do autor | Tinha dado macro-F1 0,265; multi-large deu 0,288 |
| D-08 | Sem Docker/React/streaming | Critérios do challenge; orçamento de tempo |

## Erros da IA (ou dos docs gerados por IA) que foram pegos

1. `Ticket Type` com 3 classes (README) → são 5.
2. "156 placeholders distintos" → depende do regex; o código declara o regex.
3. Schema Pioneer `multi_label:false, top_k:3` → resposta vazia.
4. GLiFormer no Pioneer → ausente do catálogo.
5. Política sem guarda de domínio → roteava ticket de outro domínio.
6. Máscara de `.env` que esperava `=` → vazou a chave no log (**rotacionar**).
7. `value=` em widget com `key` no Streamlit → botão não atualizava o texto.
8. Cliente urllib sem keep-alive → ~4 s por chamada ao Pioneer; resolvido com cache em blocos.
9. Lints do clippy em funções auxiliares de teste (`allow-unwrap-in-tests` só vale para `#[test]`).
10. Fallback só para erro HTTP → abstenção `null` do multi-large passava como "sem rótulo".
11. Guardrail marcando nosso `[PERSON]`, "specialist" (induzido pelo meu próprio prompt), "you" e "today." como PII.
12. LLM com `max_tokens` baixo devolve conteúdo vazio (gasta os tokens raciocinando).
13. Teste de Recall@k com expectativa errada (escrevi 0,5; o correto é 1,0).
14. Comando `cargo run --manifest-path` documentado não funcionava fora de `router/` (rustup escolhe a versão pela pasta atual).
15. Porta fixa 18080 nos testes colidia com o OrbStack → portas escolhidas pelo sistema.
16. Varredura de segredos com `grep` pulava arquivos ocultos → refeita em Python.
17. `vercel_runtime` não compila para Windows → dependência só em Unix.
18. Sobrescrever binário assinado no macOS com `cp` → SIGKILL; o build agora grava arquivo novo.
19. Bootstrap do app público rodava o pipeline inteiro → no Linux o cache do Pioneer ficava incompleto e o app pedia chave.
20. `pyarrow` 25.0.1 com segfault conhecido → fixado abaixo de 25.
21. Cache do `router_status` sem o endereço como chave → testes com portas diferentes reaproveitavam o status errado.

## Como reproduzir as provas

```bash
cd solution
uv run pytest -q                 # 87 testes: unitários, cargo test, clippy e E2E Playwright
for f in $(ls .spec/features); do onp-spec verify $f; done
onp-spec audit --ci              # só as perguntas de negócio abertas aparecem
```

## Evidências

- `chat-exports/sessao-claude-code-002.md`: conversa legível (chave e e-mail redigidos).
- `chat-exports/sessao-claude-code-002.jsonl.gz`: transcript completo, redigido.
- `screenshots/e2e-*.png`: capturas geradas pelos testes Playwright.
