# Proposal: validacao-features

## Why

O documento *Features Engineering* do candidato propõe 20 features com janelas
de 90 dias e reporta uma triagem própria (conta × snapshot mensal, rótulo =
evento de churn não-reativação em 30 dias): ROC-AUC 0,604 e AP 0,144, com
`tenure_days` dominando a importância por permutação (+0,043 contra ≤ +0,003 de
todas as outras).

A matriz de features (`docs/04-matriz-de-features.md`) mostrou três lacunas que
só se resolvem medindo:

1. **Taxas não medidas aqui.** `errors_per_100_uses`, `escalation_rate` e
   `satisfaction_missing_share` existem no diagnóstico como *contagens*. A
   referência vê sinal justamente nas taxas.
2. **Unidade diferente.** A referência trabalha por conta; este projeto, por
   assinatura. Não dá para saber se `tenure_days` (idade da conta) e `age_days`
   (idade da assinatura) são o mesmo sinal sem construir as duas.
3. **Flags sem data.** `upgrade_flag`, `downgrade_flag` e `auto_renew_flag` não
   têm carimbo de tempo: nenhum dos dois projetos consegue provar que são
   anteriores ao corte.

## What Changes

- Features de taxa com regra de denominador explícita, em dois recortes: janela
  de 90 dias (como a referência) e todo o histórico anterior ao corte.
- Painel por conta que **replica o desenho da referência** (snapshots mensais,
  janelas de 90 dias, rótulo de evento de churn em 30 dias, treino até
  31/08/2024) — comparável número a número com a triagem do candidato.
- Triagem univariada com correção de Holm para as taxas e comparação direta
  entre idade da conta e idade da assinatura.
- **Quarentena das flags sem data**: saem da matriz de features do diagnóstico
  e de qualquer painel novo (princípio P-009).

## Impact

- **Muda números publicados:** ao remover as flags, a logística e o GBM do
  `oot_validation.csv` são reestimados; o relatório e o README acompanham (os
  números são conferidos por teste).
- **Não muda o score de produção** (risco por idade da assinatura) nesta etapa —
  se as taxas tiverem sinal, entrar no score é decisão do dono do produto (Q-003).
- **Fora de escopo:** tendência de uso e recência (`usage_trend_ratio_90d`,
  `days_since_last_usage`) seguem descartadas enquanto a instrumentação não for
  corrigida (ação 3 do relatório).
