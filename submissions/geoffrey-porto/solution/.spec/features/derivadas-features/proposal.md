# Proposal: derivadas-features

## Why

A referência (*Features Engineering*) sugere três features compostas "mais
acionáveis que os valores isolados". Duas são construíveis hoje:
`usage_per_active_seat_90d` e `support_friction_index`. A terceira
(`commercial_contraction_flag`) depende de flags sem data e segue bloqueada.

Elas nunca foram medidas aqui — e, enquanto não forem, o registro de features
carrega duas linhas "⬜ ainda não construída". Fase B do plano de completude.

## What Changes

- `usage_per_active_seat_90d`: uso da janela dividido pelos assentos ativos.
- `support_friction_index`: soma de quatro z-scores de atrito de suporte, com os
  parâmetros (média e desvio) **ajustados só no treino** — z-score ajustado no
  painel inteiro vazaria o teste para dentro da feature.
- As duas entram na triagem univariada com correção de Holm junto com as demais.
- Registro e matriz passam de ⬜ para ✅ automaticamente (teste da fase A).

## Impact

- **Não entram na replicação da referência** (que reproduz a lista publicada) nem
  no score de produção; são candidatas em avaliação.
- Expectativa honesta: com 12 hipóteses e 13 features já medidas sem sinal, o
  resultado provável é "sem sinal" também aqui. O valor é fechar a pergunta.
