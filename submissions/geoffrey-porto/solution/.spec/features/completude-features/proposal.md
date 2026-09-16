# Proposal: completude-features

## Why

A matriz de features (`docs/04-matriz-de-features.md`) classificava 8 features
da referência como "parciais" — mas o painel por conta do incremento 2 já
implementa **15 das 20** features e **os 8 controles** na forma original. O
status da matriz descrevia só o painel do diagnóstico e ficou desatualizado em
relação ao código: exatamente o tipo de mentira silenciosa que o SDD existe
para impedir.

O risco não é teórico: a contagem publicada na matriz estava errada (dizia 11
parciais; a tabela tinha 8), porque era mantida à mão.

## What Changes

- **Registro único** (`features.REFERENCE_FEATURES`): as 20 features, os 8
  controles e as 3 derivadas da referência, cada uma com status, a coluna que a
  implementa e o painel onde vive — ou o motivo de não existir.
- **Teste mecânico** que cruza o registro com as colunas reais dos dois painéis:
  quem está marcada como implementada tem coluna de verdade; quem não está tem
  motivo escrito.
- **Tabelas do documento alinhadas ao registro**, com legenda sem ambiguidade
  (implementada / em quarentena / excluída por linha do tempo).

## Impact

- Acaba o status "parcial" ambíguo: ou a feature existe (e o teste prova onde),
  ou não existe (e o motivo está escrito).
- Não muda modelo, score nem números do relatório — é fase de verdade
  documental, não de engenharia de features.
- **Fora de escopo (fases B–D do plano):** derivadas novas
  (`usage_per_active_seat_90d`, `support_friction_index`), as duas features de
  linha do tempo medidas sob bandeira, e o contrato de dados que destravaria as
  três flags sem data.
