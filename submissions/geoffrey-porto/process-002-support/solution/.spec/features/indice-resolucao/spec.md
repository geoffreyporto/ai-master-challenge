# Spec: Índice de tickets similares (base para respostas sugeridas)

> feature: indice-resolucao
> status: em-implementacao

## Contexto

O agente ganha tempo quando vê tickets parecidos já tratados. Nenhum dos
datasets tem resolução real (as do Dataset 1 são frases aleatórias), então o
índice é medido pelo que dá para medir: se os vizinhos recuperados são da
mesma fila do ticket consultado.

## Histórias

### US-006 — O agente vê tickets parecidos já tratados ao abrir um ticket novo

Como agente de suporte, quero os k tickets mais parecidos já tratados, para
reaproveitar a solução em vez de começar do zero.

#### AC-018 — O índice é construído só com o treino

- **Dado** o índice de similares
- **Quando** ele é consultado com um ticket do teste
- **Então** nenhum documento do teste está no índice

#### AC-019 — Recall@k é medido no hold-out inteiro

- **Dado** todos os tickets do teste como consulta
- **Quando** os k vizinhos mais próximos são recuperados (k = 1, 5, 10)
- **Então** Recall@k (fração de consultas com ao menos um vizinho da mesma fila) é reportado
- **E** Recall@5 supera o acerto esperado por sorteio proporcional às classes

#### AC-020 — A limitação das resoluções é declarada

- **Dado** o texto de resolução do Dataset 1
- **Quando** o relatório descreve respostas sugeridas
- **Então** ele declara que as resoluções são sintéticas e que Recall@k mede a fila, não a qualidade da resposta

## Fora de escopo

- Gerar rascunho de resposta com LLM (sem resolução real para ancorar).
- Detecção de duplicatas em produção (o Dataset 2 tem zero duplicatas exatas).

## Suposições

| ID | Suposição | Status | Resolução |
|---|---|---|---|
| ASM-006 | Mesma fila é um proxy aceitável de "ticket útil como referência" | aberta | É um limite inferior honesto; a utilidade real exige avaliação por agentes. |

## Perguntas em aberto

Nenhuma.
