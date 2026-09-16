# Spec: Features de linha do tempo e contrato de dados

> feature: linha-do-tempo
> status: implementada

## Contexto

Fechar os cinco itens que sobraram: medir o que dá para medir sob bandeira e
transformar o que não dá em pedido formal para Engenharia.

## Histórias

### US-012 — Diretoria sabe quanto vale consertar a instrumentação

Como CEO, quero saber se as features que dependem da data de uso teriam sinal
caso os dados fossem confiáveis, para decidir se a correção vale o esforço.

#### AC-031 — As duas features existem nos dois recortes

- **Dado** a janela de 90 dias antes do corte
- **Quando** as features de linha do tempo são calculadas
- **Então** saem a razão de tendência de uso e os dias desde o último uso, no dado bruto e no subconjunto consistente (uso dentro da janela da assinatura)
- **E** uma conta sem uso no recorte fica com valor vazio

#### AC-032 — Elas não entram no score nem na replicação

- **Dado** o conjunto de features marcadas como não confiáveis
- **Quando** o score de produção e a replicação da referência são montados
- **Então** nenhuma delas aparece nas colunas usadas
- **E** a lista de features não confiáveis fica declarada em um único lugar

#### AC-033 — As duas são medidas com correção de Holm

- **Dado** o painel de triagem
- **Quando** a triagem roda
- **Então** os quatro valores (duas features × dois recortes) saem com AUC, p ajustado e tamanho de amostra
- **E** o resultado do recorte consistente aparece separado do recorte bruto

### US-013 — Engenharia recebe um pedido específico, não uma reclamação

Como time de dados, quero saber exatamente quais campos faltam e como saber que
o problema foi resolvido, para poder priorizar a correção.

#### AC-034 — O contrato cobre todo item bloqueado, com teste de aceitação

- **Dado** o registro de features da referência
- **Quando** o contrato de dados é conferido
- **Então** todo item em quarentena, excluído ou medido sob bandeira aparece no contrato
- **E** cada linha do contrato traz o campo que falta e o teste que destrava o item

## Fora de escopo

- Corrigir a instrumentação (é trabalho de Engenharia; aqui entra o pedido).
- Usar as features de linha do tempo no score enquanto o contrato não for cumprido.

## Suposições

| ID | Suposição | Status | Resolução |
|---|---|---|---|
| ASM-014 | Uso "consistente" = evento com data dentro da janela da assinatura (`start_date` ≤ data ≤ `end_date`) | confirmada | 5.568 de 25.000 eventos (22,3%), cobrindo 469 das 500 contas — amostra suficiente para medir no recorte de teste. |

## Perguntas em aberto

| ID | Pergunta | Status | Resposta |
|---|---|---|---|
| — | Nenhuma. | — | — |
