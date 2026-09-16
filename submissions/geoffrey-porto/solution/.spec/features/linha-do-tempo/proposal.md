# Proposal: linha-do-tempo

## Why

Sobraram cinco itens da referência sem medição, todos pelo mesmo motivo de
fundo: **campos sem carimbo de tempo confiável**.

- `usage_trend_ratio_90d` e `days_since_last_usage` dependem da data do uso, e
  76,6% do uso é anterior ao início da assinatura a que está ligado.
- `auto_renew_share`, `upgrade_share` e `downgrade_share` (e a derivada
  `commercial_contraction_flag`) são flags sem data nenhuma.

Descartá-las sem número foi a decisão certa para o score, mas deixa uma
pergunta em aberto para o negócio: **quanto se ganharia se a instrumentação
fosse corrigida?** Dá para responder em parte hoje — 22,3% dos eventos de uso
(5.568) caem dentro da janela da assinatura e formam um subconjunto consistente.

## What Changes

- As duas features de linha do tempo são construídas e medidas **sob bandeira**:
  em dois recortes (dado bruto e subconjunto consistente), fora do score de
  produção e fora da replicação da referência, com teste que garante o bloqueio.
- Um **contrato de dados** (fase D) lista, item por item bloqueado, o campo que
  Engenharia precisa entregar e o teste de aceitação que o destrava.
- Um teste garante que todo item bloqueado do registro aparece no contrato —
  nada fica "descartado e esquecido".

## Impact

- Responde com número a "vale a pena consertar a instrumentação?".
- Não muda score, relatório nem replicação.
- Encerra o plano de completude: depois disto, cada uma das 31 linhas do
  registro está implementada, medida sob bandeira ou com contrato de dados.
