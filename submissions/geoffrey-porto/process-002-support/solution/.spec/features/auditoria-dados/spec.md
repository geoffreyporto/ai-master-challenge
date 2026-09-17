# Spec: Auditoria de autenticidade dos dados

> feature: auditoria-dados
> status: em-implementacao

## Contexto

Antes de qualquer diagnóstico, o Diretor precisa saber se os números dos dois
datasets descrevem uma operação real. O README promete "~30.000 registros com
texto real"; o arquivo precisa provar isso ou ser declarado sintético.

## Histórias

### US-001 — O Diretor sabe se pode confiar nos dados antes de ler o diagnóstico

Como Diretor de Operações, quero um veredito de autenticidade com evidência
para cada dataset, para não tomar decisão em cima de ruído.

#### AC-001 — O Dataset 1 recebe veredito com a evidência que o sustenta

- **Dado** o arquivo `customer_support_tickets.csv`
- **Quando** a auditoria roda
- **Então** o veredito é `sintetico`
- **E** a evidência mostra a fração de descrições com `{product_purchased}`, o p-valor χ² de uniformidade de tipo, status, prioridade, canal e produto, a fração de tickets fechados "resolvidos antes da primeira resposta" e os domínios de e-mail

#### AC-002 — O Dataset 2 recebe veredito com a evidência que o sustenta

- **Dado** o arquivo `all_tickets_processed_improved_v3.csv`
- **Quando** a auditoria roda
- **Então** o veredito é `real_preprocessado`
- **E** a evidência mostra zero placeholders, zero duplicatas, zero rótulos conflitantes, a razão entre a maior e a menor classe e a ausência de maiúsculas e dígitos

#### AC-003 — Divergências entre o README do challenge e o arquivo aparecem declaradas

- **Dado** o que o README do challenge descreve
- **Quando** a auditoria compara com o arquivo
- **Então** cada divergência aparece com o valor prometido e o medido (volume de linhas e número de tipos de ticket)

## Fora de escopo

- Corrigir ou "consertar" o dataset sintético.
- Qualquer conclusão de negócio (vem em `diagnostico-operacional`).

## Suposições

| ID | Suposição | Status | Resolução |
|---|---|---|---|
| ASM-001 | Distribuições uniformes em todas as categorias + intervalos temporais impossíveis bastam para declarar o Dataset 1 sintético | confirmada | Operação real não tem 5 tipos, 4 canais, 4 prioridades e 42 produtos todos uniformes ao mesmo tempo (χ² p ≥ 0,11) nem 49% de tickets resolvidos antes da primeira resposta. |

## Perguntas em aberto

| ID | Pergunta | Status | Resposta |
|---|---|---|---|
| Q-001 | A empresa tem um export real do help desk (timestamps por mudança de estado, agente, reaberturas) para substituir o Dataset 1? | aberta | Estrutura completa em `docs/04-perguntas-em-aberto.md`. Sem isso, o diagnóstico de gargalo é pipeline pronto + resultado nulo. |
