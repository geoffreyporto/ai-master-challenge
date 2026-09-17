# Grafo do código-fonte (graphify)

Gerado com [graphify](https://github.com/Graphify-Labs/graphify) 0.9.32 sobre
`solution/src`, `solution/app`, `solution/tests` e `solution/router/{src,tests}`
— extração local por AST, **sem LLM** (custo de tokens: 0).

| Arquivo | Conteúdo |
|---|---|
| `graph.html` | Grafo interativo (abrir no navegador) |
| `graph.json` | Nós, arestas e comunidades |
| `GRAPH_REPORT.md` | Resumo: nós centrais, conexões inferidas, ciclos, comunidades |

Resultado: 504 nós, 951 arestas, 27 comunidades, **nenhum ciclo de import**.

## Como regenerar

```bash
graphify update solution --no-cluster
graphify cluster-only solution --no-label
```

(rodar numa cópia só com o código, para não varrer `.venv/` e `router/target/`)

## O que o grafo mostrou

- **Ciclo de import no roteador Rust** (`model.rs ↔ policy.rs`): cada um
  importava um tipo do outro. Corrigido movendo `Scores` para
  `router/src/scores.rs`; a segunda execução não acusa ciclo.
- **Nós centrais**: `run()` (pipeline), `PioneerClient`, `TfidfLR`,
  `RouterModel`, `Decision`, `Policy` — o núcleo coincide com a arquitetura
  (`docs/05-arquitetura-solucao.html`).
- **Conexões inferidas úteis**: `similar()` do app chama o mesmo `normalize()`
  do treino (P-005); `route()` do Rust chama `decide()` da política.

## Leitura das comunidades

Os nomes ficam como `Community N` porque a nomeação automática exige um LLM
(`--no-label`). As maiores correspondem a: rascunho + classificação hospedada;
leitura de dados e configuração; modelo Rust (normalização, n-gramas); HTTP do
roteador (axum); política IA × humano; diagnóstico estatístico; índice de
similares; lançador dos binários; auditoria; app Streamlit; e um grupo por
arquivo de teste (as docstrings `@spec:AC-xxx` aparecem como nós).
