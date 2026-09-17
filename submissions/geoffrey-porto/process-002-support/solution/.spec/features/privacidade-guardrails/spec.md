# Spec: Privacidade e guardrails de PII

> feature: privacidade-guardrails
> status: em-implementacao

## Contexto

Ticket de suporte carrega nome, e-mail, telefone e endereço do cliente. Antes
de qualquer texto sair para um LLM hospedado, a PII é mascarada
(`fastino/gliner2-privacy-filter-PII-multi`); antes de qualquer rascunho
aparecer para o agente, um guardrail procura PII na saída
(`fastino/gliguard-PII-multi`).

## Histórias

### US-011 — O dado do cliente não vaza para o modelo nem para a resposta

Como responsável por privacidade, quero que a PII seja mascarada antes do LLM
e barrada na saída, para usar IA generativa sem expor clientes.

#### AC-033 — A máscara encontra nome e e-mail do cliente

- **Dado** uma amostra sorteada com semente de tickets do Dataset 1 com o nome e o e-mail do cliente inseridos no texto
- **Quando** o filtro de privacidade mascara cada texto
- **Então** o recall de nomes mascarados é ≥ 0,90 e o de e-mails é ≥ 0,95, e os dois são reportados

#### AC-034 — Nenhum texto chega ao LLM sem máscara

- **Dado** um ticket com PII
- **Quando** o rascunho é pedido
- **Então** o texto enviado ao LLM é o mascarado e não contém o nome nem o e-mail originais
- **E** se o filtro de privacidade falhar, nenhum texto é enviado ao LLM

#### AC-035 — O guardrail barra rascunho com PII

- **Dado** um rascunho com e-mail ou telefone e outro sem PII
- **Quando** o guardrail avalia os dois
- **Então** o primeiro é bloqueado com as entidades encontradas e o segundo passa

## Fora de escopo

- Reidentificação (o mapa de placeholders não é guardado).
- PII em anexos ou imagens.

## Suposições

| ID | Suposição | Status | Resolução |
|---|---|---|---|
| ASM-009 | Nome e e-mail inseridos a partir das colunas do Dataset 1 representam a PII real dos tickets | aberta | São dados Faker; servem para medir recall, não para estimar a PII real da operação. |

## Perguntas em aberto

| ID | Pergunta | Status | Resposta |
|---|---|---|---|
| Q-004 | A empresa autoriza enviar texto de ticket (mascarado) a um provedor hospedado (Pioneer / DeepSeek)? | aberta | Estrutura completa em `docs/04-perguntas-em-aberto.md`. Decisão na ausência: só texto mascarado, `store:false`; benchmark só com o Dataset 2 público. |
