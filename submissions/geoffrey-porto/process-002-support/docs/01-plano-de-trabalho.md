# Plano de trabalho — Challenge 002 (Redesign de Suporte)

Orçamento: **4–6 h** (meta interna < 4 h de execução + revisão). Método:
CRISP-DM para a análise, onp-spec (SDD) para o código. Cada marco termina com
uma prova: teste verde, número em `outputs/metrics.json` ou `onp-spec audit`.

## Objetivos (as três perguntas do Diretor)

| Pergunta | Entrega | Prova |
|---|---|---|
| Onde perdemos tempo? | Auditoria + diagnóstico com teste, efeito e poder | `auditoria-dados`, `diagnostico-operacional` |
| O que automatizar (e o que não)? | Classificador + fronteira medida IA × humano | `classificador-tickets`, `fronteira-automacao` |
| Mostre funcionando | App Streamlit + roteador Rust no hold-out inteiro | `prototipo` |
| Quanto economiza? | Cenário de ROI com premissas explícitas | `cenario-roi` |

## Marcos

| # | Janela | Marco | Tarefas-chave | Critério de saída |
|---|---|---|---|---|
| M0 | 0:00–0:30 | Entender e verificar | Ler regras, README, docs de referência; baixar datasets; **re-medir** as afirmações dos docs; smoke test Pioneer | Divergências registradas (tipos de ticket, placeholders, schema Pioneer) |
| M1 | 0:30–1:00 | Especificar (SDD) | Constituição (P-001…P-011), 8 features com US/AC, suposições e perguntas; plano e guia | `onp-spec audit` só acusa AC sem teste |
| M2 | 1:00–1:45 | Auditoria + diagnóstico (T-001, T-002) | Veredito dos dois datasets; KW + ε², MDE, logit ordinal; achados rotulados | AC-001…AC-008 verdes |
| M3 | 1:45–2:30 | Modelos (T-003, T-004) | Split 70/10/20; B0 TF-IDF+LR; B1 Model2Vec+LR; B2 GLiNER2 zero-shot (Pioneer, cache); ECE | AC-009…AC-012 verdes |
| M4 | 2:30–3:00 | Fronteira + similares + cruzamento (T-005…T-007) | Limiares por fila, conformal, política; Recall@k; KS D1×D2 | AC-013…AC-022 verdes |
| M5 | 3:00–3:45 | Protótipo (T-008…T-011) | ROI; pipeline e export; roteador axum com paridade; app Streamlit | AC-023…AC-029 verdes; app aberto no navegador |
| M6 | 3:45–4:30 | Fechamento (T-012) | README com números conferidos, process log, `onp-spec verify` + `audit`, revisão humana | Checklist do CONTRIBUTING completo |
| (opcional) | +30–60 min | GLiNER2 LoRA (B4) | Upload do split pelo dashboard Pioneer (não há endpoint de upload), job de treino, reavaliação no mesmo hold-out | Linha B4 na tabela de benchmark |

## Caminho crítico e riscos

| Risco | Mitigação |
|---|---|
| Dataset 1 sintético (confirmado) | Reenquadrar entrega 1: auditoria + pipeline pronto + resultado nulo com poder; desperdício via cenário |
| Zero-shot GLiNER2 fraco em texto sem stopwords | Reportar honestamente; modelo de produção escolhido na validação |
| Paridade Python ↔ Rust | Analisador de n-gramas próprio e simples; teste no hold-out inteiro |
| Chave Pioneer | Só por variável de ambiente/arquivo fora do repo; cache dos resultados para o teste não chamar a API |
| Tempo | Sem Docker/K8s/React/microserviços; Erlang C e cleanlab ficam fora (YAGNI) |

## Definição de pronto

- `uv run pytest` verde; `cargo test` verde (chamado pelo pytest).
- `onp-spec verify <feature>` para as 8 features; `onp-spec audit --ci` sem erro além das perguntas de negócio mantidas abertas (Q-001…Q-003).
- README da submissão no template, com números marcados e conferidos.
- Só arquivos dentro de `submissions/geoffrey-porto/` no PR; dados e chaves fora do commit.
