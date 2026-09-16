# Spec: Completude do mapa de features

> feature: completude-features
> status: implementada

## Contexto

Fazer o mapa entre as features da referência e o que o projeto realmente
implementa parar de ser mantido à mão — e virar algo que a máquina confere.

## Histórias

### US-010 — Avaliador confia no status de cada feature da referência

Como avaliador, quero que o status de cada feature da referência seja verificado
contra o código, para que a matriz não envelheça em silêncio.

#### AC-025 — O registro cobre a referência inteira e bate com os painéis

- **Dado** o registro de features da referência
- **Quando** o teste de completude roda
- **Então** as 20 features, os 8 controles e as 3 derivadas da referência estão no registro
- **E** toda feature marcada como implementada aponta uma coluna que existe no painel indicado
- **E** toda feature não implementada traz o motivo escrito

#### AC-026 — A tabela do documento reflete o registro

- **Dado** a matriz de features publicada
- **Quando** o teste de consistência roda
- **Então** cada feature da referência aparece na tabela com o mesmo status do registro
- **E** a contagem publicada (implementadas, em quarentena, excluídas) bate com o registro

## Fora de escopo

- Criar features novas (fases B–D do plano): derivadas, features de linha do
  tempo sob bandeira e o contrato de dados das flags sem data.
- Mudar o score de produção ou qualquer número do relatório.

## Suposições

| ID | Suposição | Status | Resolução |
|---|---|---|---|
| ASM-011 | A lista da referência é fechada: 20 features, 8 controles e 3 derivadas | confirmada | Conferida no documento `docs/referencia/Features Engineering.md` e no `feature_columns` da triagem publicada. |

## Perguntas em aberto

| ID | Pergunta | Status | Resposta |
|---|---|---|---|
| — | Nenhuma. | — | — |
