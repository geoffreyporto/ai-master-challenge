# Spec: Validação das features da referência

> feature: validacao-features
> status: em-implementacao

<!--
  Formato verificado por `onp-spec audit`.
  Códigos continuam a numeração global da feature diagnostico-churn.
-->

## Contexto

Medir, em vez de opinar, três pontos abertos pela matriz de features: as
features de taxa da referência têm sinal aqui? Idade da conta e idade da
assinatura são o mesmo sinal? E o que acontece com o diagnóstico quando as
flags sem data saem da matriz?

## Histórias

### US-007 — Analista sabe se as features de taxa da referência têm sinal aqui

Como analista, quero medir as três taxas apontadas pela referência, para que a
decisão de incluí-las no score seja por evidência e não por intuição.

#### AC-019 — As taxas têm regra de denominador explícita

- **Dado** uma conta sem nenhum uso registrado e outra sem nenhum ticket
- **Quando** as taxas são calculadas
- **Então** `errors_per_100_uses` fica vazia para quem não tem uso e `escalation_rate` e `satisfaction_missing_share` ficam vazias para quem não tem ticket
- **E** com dados presentes, os valores batem com a conta feita à mão (ex.: 3 erros em 150 usos = 2,0)

#### AC-020 — A triagem univariada mede cada taxa com correção para múltiplas comparações

- **Dado** o painel de validação e as três taxas nos dois recortes (90 dias e histórico completo)
- **Quando** a triagem roda
- **Então** a tabela traz, por feature, a área sob a curva ROC, o p-valor ajustado por Holm e o tamanho da amostra
- **E** o resultado sai em `outputs/feature_screening.csv`

### US-008 — Time de dados compara o desenho da referência com o desta entrega

Como time de dados, quero o painel por conta do jeito da referência, para saber
se a diferença de resultado vem das features ou da unidade de análise.

#### AC-021 — O painel por conta replica o desenho da referência

- **Dado** os cinco CSVs
- **Quando** o painel de contas é construído
- **Então** cada linha é uma conta num fim de mês, as features olham 90 dias para trás e o rótulo é evento de churn não-reativação nos 30 dias seguintes
- **E** o relatório mostra a área sob a curva ROC e a precisão média no mesmo recorte de teste da referência (a partir de 31/08/2024)

#### AC-022 — O painel por conta não enxerga o futuro

- **Dado** uma data de corte de snapshot
- **Quando** todos os eventos com data igual ou posterior ao corte são apagados
- **Então** nenhuma feature do painel muda
- **E** o rótulo usa apenas eventos na janela seguinte ao corte

#### AC-023 — A comparação entre idade da conta e idade da assinatura é explícita

- **Dado** o painel por conta com idade da conta e idade da assinatura mais nova
- **Quando** a comparação roda
- **Então** a tabela traz a área sob a curva de cada uma, a correlação entre elas e o resultado do modelo com cada uma sozinha e com as duas juntas
- **E** o veredito ("mesmo sinal" ou "sinais distintos") sai escrito na saída

### US-009 — Ninguém usa campo sem data como feature preditiva

Como responsável pelo modelo, quero que campos sem carimbo de tempo fiquem fora
das features, para que "medido antes do corte" seja verificável e não uma
promessa.

#### AC-024 — As flags sem data não entram em nenhuma matriz de features

- **Dado** os painéis de validação (por assinatura e por conta)
- **Quando** a matriz de features é montada
- **Então** `upgrade_flag`, `downgrade_flag` e `auto_renew_flag` não aparecem em nenhuma coluna
- **E** a lista de campos em quarentena fica declarada em um único lugar do código

## Fora de escopo

- Tendência e recência de uso (`usage_trend_ratio_90d`, `days_since_last_usage`):
  dependem da correção da instrumentação (ação 3 do relatório).
- Trocar o score de produção: decisão do dono do produto (Q-003).
- Reescrever a triagem da referência em pandas: a replicação é em Polars, com o
  mesmo desenho, e as diferenças ficam registradas.

## Suposições

| ID | Suposição | Status | Resolução |
|---|---|---|---|
| ASM-007 | O rótulo da referência é "evento de churn não-reativação nos 30 dias seguintes ao snapshot", diferente do rótulo desta entrega (assinatura encerrada em 92 dias) | confirmada | Lido no script da referência (`docs/referencia/screen_ravenstack_features.py`), linhas do bloco `future = churn.loc[...]`. A replicação usa o rótulo da referência para ser comparável. |
| ASM-008 | Medir as taxas em janela de 90 dias herda o problema de linha do tempo (ASM-004) | confirmada | 76,6% do uso é anterior à assinatura. Por isso a triagem reporta os dois recortes: 90 dias e histórico completo. |
| ASM-009 | Remover as flags sem data não piora o diagnóstico de forma relevante | aberta | **Medido:** sem as flags, a logística foi de 0,53 para 0,53 e o GBM de 0,52 para 0,53 fora do tempo — não piorou. Falta o dono do produto confirmar que aceita a quarentena como política permanente. |
| ASM-010 | Plano, assentos, MRR e frequência de cobrança descrevem a assinatura **desde o início**, e não só o estado na extração | aberta | O dataset não tem histórico dessas colunas: se forem mutáveis (como as flags em quarentena), o mesmo problema de data se aplica a elas. Registrado como risco declarado; validação junto com a ação 3 do relatório (instrumentação). |

## Perguntas em aberto

| ID | Pergunta | Status | Resposta |
|---|---|---|---|
| Q-003 | Se alguma taxa tiver sinal fora do tempo, ela entra no score de produção (hoje só idade × MRR) ou espera a correção da instrumentação? | aberta | — Decisão do dono do produto, depois de ver `feature_screening.csv`. |
