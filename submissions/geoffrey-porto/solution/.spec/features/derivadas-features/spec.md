# Spec: Features derivadas da referência

> feature: derivadas-features
> status: implementada

## Contexto

Construir e medir as duas features compostas que a referência recomenda e que os
dados permitem, sem repetir o erro de deixar o z-score olhar o futuro.

## Histórias

### US-011 — Analista mede as derivadas recomendadas pela referência

Como analista, quero as duas features compostas construídas com regra explícita
de vazio e medidas como as demais, para decidir por evidência se valem algo.

#### AC-027 — Uso por assento tem fórmula e regra de vazio explícitas

- **Dado** uma conta com assinaturas ativas na janela
- **Quando** o uso por assento é calculado
- **Então** o valor é o uso da janela dividido pelos assentos ativos (mínimo 1)
- **E** uma conta sem nenhum uso na janela recebe zero, não vazio

#### AC-028 — O índice de atrito é ajustado só no treino

- **Dado** o painel dividido em treino e teste
- **Quando** o índice de atrito é calculado
- **Então** a média e o desvio de cada componente vêm apenas das linhas de treino
- **E** uma conta sem ticket na janela fica com índice vazio, não zero

#### AC-029 — As duas derivadas entram na triagem com as demais

- **Dado** o painel por conta com as derivadas
- **Quando** a triagem univariada roda
- **Então** as duas aparecem com AUC, p ajustado por Holm e tamanho de amostra
- **E** o registro de features passa a apontar a coluna que implementa cada uma

#### AC-030 — Derivada com sinal é decomposta antes de virar achado

- **Dado** uma feature composta que apareça como significativa na triagem
- **Quando** a decomposição roda
- **Então** a tabela mostra a área sob a curva da composta, do numerador e do inverso do denominador
- **E** mostra a correlação da composta com o denominador, para revelar se o sinal é do denominador

## Fora de escopo

- `commercial_contraction_flag`: depende de duas flags em quarentena (P-009).
- Entrar no score de produção ou na replicação da referência.

## Suposições

| ID | Suposição | Status | Resolução |
|---|---|---|---|
| ASM-012 | As quatro componentes do atrito faltam em bloco: ou a conta teve ticket na janela, ou nenhuma delas existe | confirmada | Conferido no painel: 2.589 de 4.246 linhas sem ticket, com as quatro colunas vazias juntas. Por isso o índice é vazio (e não zero) nessas linhas. |
| ASM-013 | Assentos ativos são sempre ≥ 1 quando a conta tem assinatura ativa | confirmada | Conferido no painel: nenhuma linha com `active_seats` ≤ 0. O `max(…, 1)` da fórmula da referência fica como guarda defensiva. |

## Perguntas em aberto

| ID | Pergunta | Status | Resposta |
|---|---|---|---|
| — | Nenhuma. | — | — |
