# Proposal: diagnostico-churn

> Formato OpenSpec (`proposal → design → tasks → apply → archive`). O motor
> mecânico de auditoria é o onp-spec (`spec.md` + testes `@spec:AC-xxx`).

## Why

O CEO recebe três sinais que "não batem": churn subindo, satisfação ok, uso
crescendo. Sem um diagnóstico cruzando as cinco tabelas, a empresa vai reagir
ao sintoma mais visível (ex.: "melhorar o suporte") sem saber se ele explica
alguma coisa. A descoberta inicial (fase 2 do CRISP-DM) mostrou que o problema
é maior que "qual variável prevê churn":

1. **O churn subiu em contagem porque a base cresceu ~6×** — a taxa ficou
   estável em ~1%/mês até set/2024 e só então subiu (2,5% em dez).
2. **As três definições de churn do dataset discordam** (flag da conta,
   eventos de churn, fim de assinatura).
3. **As linhas do tempo de uso e de tickets não conversam com o ciclo de vida
   do cliente** (77% do uso antes da assinatura existir).
4. **Nenhum sinal comportamental (suporte, uso, satisfação) separa quem sai de
   quem fica** — um modelo com as cinco tabelas empata com o acaso fora do
   tempo.

## What Changes

- Pipeline reprodutível (Python 3.14 + Polars) que carrega, audita e cruza as
  cinco tabelas → `outputs/metrics.json`, CSVs e figuras.
- Métricas de churn como **taxa sobre base ativa** e **risco por idade da
  assinatura**, com padronização de mix e controle estatístico.
- Registro de hipóteses H1–H12 com teste, efeito, correção de Holm e rótulo
  descrição / predição / hipótese causal.
- Score de **perda esperada de MRR** por conta + lista do CS, validado fora do
  tempo contra modelos com todas as tabelas.
- Relatório do CEO (≤ 5 páginas) com números rastreáveis e desenho de teste A/B.

## Impact

- **Quem usa:** CEO (relatório), CS (lista de contas), Dados/Eng (pipeline e
  achados de qualidade de dados).
- **Risco se não fizer:** investir em "suporte" ou "engajamento" por
  correlação que os dados não sustentam.
- **Fora de escopo:** API, dashboard web, estimação causal sem experimento.
