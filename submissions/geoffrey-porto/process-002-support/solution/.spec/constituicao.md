# Constituição — Redesign de Suporte (Challenge 002) — v1.0.0

<!--
  Princípios inegociáveis. P-xxx = código de rastreio.
  Níveis: [DEVE] obrigatório · [RECOMENDADO] forte · [PODE] permitido.
  Todo [DEVE] tem verificação executável:
    - verificação(gate): satisfeita pelo próprio audit
    - verificação(teste): @principle:P-xxx
    - verificação(proibido): `regex` em `glob`
    - verificação(obrigatório): `regex` em `glob`
-->

Contexto: um Diretor de Operações vai decidir o que automatizar com base neste
trabalho. Os três erros mais caros não são de código: (1) vender ruído de um
dataset sintético como gargalo real, (2) anunciar acurácia medida em dado que o
modelo já viu, (3) propor automação sem porta de saída para o humano. Os
princípios abaixo tornam esses erros mecanicamente detectáveis.

## P-001 [DEVE] Todo requisito tem prova executável

Nenhuma feature é declarada pronta sem `onp-spec audit --ci` limpo, exceto as
perguntas de negócio mantidas abertas de propósito (ver `docs/`).

- verificação(gate): intrínseca ao audit

## P-002 [DEVE] Métrica só vale no hold-out intocado

O split de teste do Dataset 2 nunca é usado para treinar, calibrar ou escolher
limiar. Treino, validação e teste são disjuntos e determinísticos.

- verificação(teste): @principle:P-002

## P-003 [DEVE] Nenhum número do relatório é digitado à mão

Todo número marcado no README (`<!--m:chave-->valor`) é conferido contra
`outputs/metrics.json`, gerado pelo pipeline.

- verificação(teste): @principle:P-003

## P-004 [DEVE] Automação nunca é 100%

A política de roteamento sempre mantém uma fila humana: cobertura automática
< 100% no hold-out, classes de roteamento só-humano nunca saem automáticas e
ticket `Critical` sempre pede confirmação humana.

- verificação(teste): @principle:P-004

## P-005 [DEVE] Mesma normalização no treino e no serviço

Texto passa pela mesma função `normalize` no treino, na avaliação, no app e no
roteador Rust. A paridade Python ↔ Rust é testada no hold-out.

- verificação(teste): @principle:P-005

## P-006 [DEVE] Resultado reprodutível

Toda aleatoriedade passa por uma semente única declarada na configuração.

- verificação(obrigatório): `^SEED: Final\[int\] = \d+` em `src/support_redesign/config.py`
- verificação(teste): @principle:P-006

## P-007 [DEVE] Achado sobre dado sintético carrega o rótulo

Todo achado do diagnóstico declara a base que o sustenta (`sintetico` ou
`real`) e o tipo de afirmação (`descricao`, `predicao`, `cenario`). Cenário de
ROI sempre aponta suas premissas.

- verificação(teste): @principle:P-007

## P-008 [DEVE] Processamento de dados em Polars

pandas não entra no código de produção.

- verificação(proibido): `^\s*(import pandas|from pandas)` em `src/**/*.py`

## P-009 [DEVE] Segredos nunca em código

Chaves (ex.: `PIONEER_API_KEY`, Kaggle) vêm só de variável de ambiente.

- verificação(proibido): `(sk-[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|(api[_-]?key|password|token)\s*[:=]\s*["'][^"']{8,})` em `src/**/*.py`

## P-010 [RECOMENDADO] Dados brutos são somente-leitura

O pipeline nunca escreve em `data/`; toda saída vai para `outputs/`.

- verificação(proibido): `write_(csv|parquet)\(\s*(DATA_DIR|data_dir)` em `src/**/*.py`

## P-011 [DEVE] Roteador Rust não entra em pânico em produção

`unwrap()`, `todo!()` e `dbg!()` proibidos no código do roteador (padrão
Sonatype/Fuchsia adotado em `docs/03-arquitetura-e-padroes.md`).

- verificação(proibido): `\.unwrap\(\)|todo!\(|dbg!\(` em `router/src/**/*.rs`

## P-012 [DEVE] Modelos hospedados são os definidos pelo dono do projeto

Classificação `fastino/gliner2-multi-large-v1` (fallback
`fastino/gliner2-large-v1`), guardrail `fastino/gliguard-PII-multi`, inferência
`deepseek-ai/DeepSeek-V4-Flash`, privacidade
`fastino/gliner2-privacy-filter-PII-multi`. Os IDs vivem só em `config.py`.

- verificação(obrigatório): `^PIONEER_CLASSIFIER: Final\[str\] = "fastino/gliner2-multi-large-v1"` em `src/support_redesign/config.py`
- verificação(obrigatório): `^PIONEER_LLM: Final\[str\] = "deepseek-ai/DeepSeek-V4-Flash"` em `src/support_redesign/config.py`
- verificação(proibido): `"(fastino|deepseek-ai)/` em `src/support_redesign/pioneer.py`

## P-013 [DEVE] Texto só chega ao LLM mascarado

Todo texto enviado ao LLM passa antes pelo filtro de privacidade; se o filtro
falhar, nada é enviado.

- verificação(teste): @principle:P-013
