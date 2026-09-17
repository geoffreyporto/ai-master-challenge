# Spec: Classificador de tickets

> feature: classificador-tickets
> status: em-implementacao

## Contexto

A primeira automação candidata é classificar o ticket em uma das 8 filas do
Dataset 2. O número que importa é macro-F1 no hold-out (as classes são
desbalanceadas) e se a confiança do modelo é confiável.

## Histórias

### US-004 — O Diretor sabe quão bem a IA classifica tickets, medido em dado que ela nunca viu

Como Diretor de Operações, quero a acurácia do classificador medida em um
hold-out intocado, com F1 por fila, para saber onde ele é fraco.

#### AC-009 — O split é determinístico, estratificado e disjunto

- **Dado** o Dataset 2 e a semente do projeto
- **Quando** o split é gerado duas vezes
- **Então** treino, validação e teste têm 70/10/20% das linhas, a mesma proporção de classes e nenhum documento em comum
- **E** as duas execuções produzem os mesmos índices

#### AC-010 — O baseline TF-IDF + regressão logística é medido no hold-out

- **Dado** o modelo B0 treinado só no treino
- **Quando** ele prevê o teste
- **Então** acurácia, macro-F1 e F1 por classe são reportados, com macro-F1 ≥ 0,85

#### AC-011 — O modelo de embeddings estáticos é comparado no mesmo hold-out

- **Dado** o modelo B1 (Model2Vec potion-base-8M + regressão logística) treinado só no treino
- **Quando** B0 e B1 são comparados
- **Então** o modelo de produção é escolhido por macro-F1 na validação, nunca no teste
- **E** a latência por ticket de cada modelo é reportada

#### AC-012 — A confiança do modelo é calibrada e medida

- **Dado** as probabilidades do modelo escolhido no teste
- **Quando** a calibração é avaliada
- **Então** o Expected Calibration Error (15 faixas) é reportado

#### AC-030 — O GLiNER2 hospedado é medido no hold-out inteiro, com fallback

- **Dado** o classificador `fastino/gliner2-multi-large-v1` com fallback `fastino/gliner2-large-v1` no Pioneer
- **Quando** todos os tickets do teste são classificados
- **Então** acurácia, macro-F1 e F1 por classe são reportados, junto com quantos tickets cada modelo atendeu
- **E** quando o modelo principal falha, o ticket é atendido pelo fallback em vez de ficar sem resposta

#### AC-031 — O LLM é medido como classificador em amostra sorteada

- **Dado** uma amostra estratificada e sorteada com semente do teste
- **Quando** `deepseek-ai/DeepSeek-V4-Flash` classifica cada ticket escolhendo uma das 8 filas
- **Então** acurácia, macro-F1, latência mediana e tokens são reportados na mesma amostra para B0 e para o LLM

## Fora de escopo

- Fine-tuning LoRA do GLiNER2: o Pioneer só aceita upload de dataset pelo dashboard.
- GLiFormer: ausente do catálogo do Pioneer.

## Suposições

| ID | Suposição | Status | Resolução |
|---|---|---|---|
| ASM-003 | Os rótulos de `Topic_group` são a verdade de referência | aberta | Há documentos curtos e ambíguos; ruído de rótulo limita o teto de acurácia. Não foi feita revisão humana dos rótulos. |

## Perguntas em aberto

Nenhuma.
