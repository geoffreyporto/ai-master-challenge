# Spec: Painéis por stakeholder

> feature: paineis
> status: em-implementacao

## Contexto

Cinco painéis com métricas e KPIs acionáveis, servidos por uma página
client-side alimentada pelo pipeline.

## Histórias

### US-016 — Cada stakeholder vê a parte que lhe cabe, com o nível de análise explícito

Como CEO, líder de vendas, marketing, financeiro ou CS, quero um painel com o
que aconteceu, por que aconteceu, o que vem e o que fazer, para decidir sem
pedir uma análise nova.

#### AC-044 — Os cinco painéis existem com os quatro níveis

- **Dado** o dataset e o resultado do pipeline
- **Quando** o payload dos painéis é montado
- **Então** existem os painéis ceo, vendas, marketing, financeiro e operacoes
- **E** cada um traz as seções descritivo, diagnostico, preditivo e prescritivo, com dados não vazios ou ações declaradas

#### AC-045 — Todo KPI do painel vem do pipeline

- **Dado** um KPI com chave declarada
- **Quando** o painel é montado
- **Então** a chave existe em `outputs/metrics.json` e o valor exibido é igual ao do pipeline

#### AC-046 — O que o dataset não sustenta aparece como lacuna

- **Dado** um painel
- **Quando** ele é montado
- **Então** ele declara ao menos uma lacuna com KPI e justificativa
- **E** os KPIs impossíveis (CAC, LTV, verba de mídia, login) não aparecem como número em nenhum painel

#### AC-047 — A série do painel é a mesma do relatório

- **Dado** a série mensal exibida no painel financeiro e no do CEO
- **Quando** a taxa de churn de MRR de dezembro/2024 é lida
- **Então** ela é igual à do relatório (`mrr_churn_dec24_pct`), com o mesmo numerador e denominador

## Fora de escopo

- Servidor, banco, autenticação ou atualização em tempo real.
- Qualquer estimativa para KPI ausente no dataset.

## Suposições

| ID | Suposição | Status | Resolução |
|---|---|---|---|
| ASM-019 | Painel client-side servido por arquivo estático atende ao pedido | confirmada | O pedido é explícito: "client-side only". Vendorizar d3 e tailwind mantém a página funcional sem rede. |

## Perguntas em aberto

| ID | Pergunta | Status | Resposta |
|---|---|---|---|
| Q-005 | Quem é o dono de cada painel na RavenStack, e com que cadência ele é revisado? | aberta | Depende da estrutura do time do cliente; sem isso o painel vira relatório que ninguém abre. |
