# Proposal: efeito-causal-dml

## Why

O relatório recomenda ações, mas deixa explícito que recomendar é uma afirmação
causal e que os dados observacionais não a provam. O documento de referência
(*AI & Statistic Models — Churn*) traz o método certo para tentar: Double
Machine Learning. O código publicado lá, porém, tem dois defeitos que **inventam
significância** neste dataset:

1. `KFold(shuffle=True)` — o painel empilha snapshots mensais, então a mesma
   conta cai em treino e validação. O cross-fitting deixa de ser honesto.
2. Erro-padrão sem agrupamento — o ICC do churn por conta é ≈ 0,36 com 9,7
   linhas por conta: o efeito de desenho é ≈ 4,2, ou seja, o erro-padrão
   ingênuo é cerca de **metade** do correto.

Sem sobreposição (*overlap*) verificada, um terceiro defeito entra em cena:
comparar tratados e controles que não têm equivalente do outro lado.

## What Changes

- `dml_effect(panel, treatment, outcome, confounders)` com **cross-fitting
  agrupado por conta**, **erro-padrão agrupado** e **checagem de sobreposição
  obrigatória** (com aparo e contagem do que foi aparado).
- Duas perguntas de negócio respondidas com número e intervalo:
  escalar ticket muda churn? cobrança anual muda churn?
- Poder declarado junto do resultado: efeito mínimo detectável em pontos
  percentuais, para separar "não tem efeito" de "não dá para saber".

## Impact

- Fecha o ciclo do desafio: descrição → predição → **efeito causal estimado**.
- Não muda o score nem o relatório do CEO; entra como evidência para as ações.
- **Fora de escopo:** o efeito do onboarding (ação 1 do relatório) — não existe
  registro de contato do CS nos dados, então nenhum método causal o estima.
