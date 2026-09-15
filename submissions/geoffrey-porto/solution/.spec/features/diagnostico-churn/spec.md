# Spec: Diagnóstico de churn da RavenStack

> feature: diagnostico-churn
> status: em-implementacao

<!--
  Formato verificado por `onp-spec audit`.
  US-xxx = história de usuário · AC-xxx = critério de aceite
  ASM-xxx = suposição · Q-xxx = pergunta em aberto
  Cada AC tem um teste com `@spec:AC-xxx` no título (tests/).
-->

## Contexto

O CEO vê o churn subir, o CS diz que a satisfação está ok e o Produto diz que o
uso cresceu. Esta feature entrega um diagnóstico **verificável** (cada número
sai do pipeline), separa descrição de previsão e de hipótese causal, e dá ao CS
uma lista de contas específicas para agir amanhã.

## Histórias

### US-001 — CEO sabe se pode confiar nos dados antes de decidir

Como CEO, quero saber o quanto os dados são confiáveis, para que eu não tome
decisão de milhões em cima de um artefato de medição.

#### AC-001 — As cinco tabelas carregam com o contrato de schema conferido

- **Dado** os cinco CSVs da RavenStack
- **Quando** o pipeline carrega os dados
- **Então** cada tabela tem as colunas e os tipos do contrato e o relatório mostra a contagem de linhas
- **E** um CSV com coluna faltando interrompe a execução com mensagem que nomeia a tabela e a coluna

#### AC-002 — Violações de linha do tempo aparecem quantificadas

- **Dado** eventos de uso, tickets e churn com datas
- **Quando** a auditoria de qualidade roda
- **Então** o relatório mostra quantos eventos de uso acontecem antes do início da assinatura, quantos tickets antes do cadastro da conta e quantos churns antes da primeira assinatura

#### AC-003 — Registros diferentes com o mesmo ID não são apagados

- **Dado** dois registros de uso com o mesmo `usage_id` e conteúdo diferente
- **Quando** a deduplicação roda
- **Então** os dois registros permanecem
- **E** apenas linhas 100% idênticas viram uma só

#### AC-004 — A divergência entre as definições de churn fica visível

- **Dado** o `churn_flag` da conta, a tabela de eventos de churn e o fim das assinaturas
- **Quando** as três definições são comparadas conta a conta
- **Então** o relatório mostra quantas contas cada definição marca como churn e em quantas elas discordam

### US-002 — CEO vê a tendência real do churn (taxa, não contagem)

Como CEO, quero ver o churn como taxa sobre a base ativa, para que o
crescimento da base não seja confundido com piora da retenção.

#### AC-005 — A taxa mensal usa a base ativa no primeiro dia do mês

- **Dado** assinaturas com data de início e de fim
- **Quando** o churn de um mês é calculado
- **Então** a taxa é "assinaturas encerradas no mês ÷ assinaturas ativas no primeiro dia" (em contagem e em MRR)
- **E** trials não entram no MRR

#### AC-006 — Mudança de mix não é confundida com piora

- **Dado** o risco mensal por idade da assinatura num período de referência
- **Quando** outro período é comparado
- **Então** a razão observado/esperado fica perto de 1 quando só o mix de idades mudou
- **E** fica perto de 2 quando o risco por idade dobrou

#### AC-007 — Meses fora do padrão são sinalizados

- **Dado** a série mensal de churn de MRR
- **Quando** o controle estatístico roda contra um período de referência
- **Então** os meses acima de média + 3 desvios-padrão aparecem marcados como quebra

### US-003 — CEO recebe a causa raiz com hipóteses testadas, não opiniões

Como CEO, quero que cada explicação venha com o teste que a sustenta, para que
eu saiba o que é fato, o que é previsão e o que ainda é hipótese.

#### AC-008 — Cada hipótese sai com teste, efeito e tabelas cruzadas

- **Dado** o registro de hipóteses do diagnóstico
- **Quando** o diagnóstico roda
- **Então** cada hipótese traz estatística, p-valor ajustado, tamanho de efeito e as tabelas usadas
- **E** juntas as hipóteses cruzam as cinco tabelas

#### AC-009 — P-valores são corrigidos para múltiplas comparações

- **Dado** uma lista de p-valores com resultado conhecido
- **Quando** a correção de Holm é aplicada
- **Então** os p-valores ajustados batem com os de referência

#### AC-010 — Todo achado diz se é descrição, previsão ou hipótese causal

- **Dado** os achados do diagnóstico
- **Quando** são exportados
- **Então** cada um tem exatamente um rótulo entre descrição, predição e hipótese causal
- **E** toda hipótese causal traz o experimento que a validaria

#### AC-011 — O efeito principal é testado em vários ambientes (invariância)

- **Dado** o efeito da idade da assinatura sobre o churn
- **Quando** ele é estimado separadamente por indústria, plano e canal de aquisição
- **Então** a tabela mostra a razão de risco em cada ambiente e se a direção se mantém em todos

### US-004 — CS recebe a lista de contas específicas para agir

Como gerente de CS, quero uma lista de contas ordenada por MRR em risco, para
que meu time ligue primeiro para quem mais pesa na receita.

#### AC-012 — Cada conta tem a perda esperada de MRR

- **Dado** as assinaturas ativas de uma conta e o risco por idade e plano
- **Quando** a conta é pontuada
- **Então** a perda esperada é a soma de risco × MRR das assinaturas ativas pagas
- **E** assinaturas trial contribuem zero

#### AC-013 — A lista do CS é acionável

- **Dado** o score de todas as contas
- **Quando** a lista é exportada
- **Então** o CSV traz conta, nome, MRR ativo, perda esperada, assinaturas jovens, motivo e ação sugerida, ordenado da maior para a menor perda

#### AC-014 — A validação fora do tempo não vaza o futuro

- **Dado** uma data de corte T0
- **Quando** o painel de validação é montado
- **Então** nenhuma variável usa dado igual ou posterior a T0 e o rótulo só olha o período após T0
- **E** o relatório mostra ROC-AUC, PR-AUC, lift@10% e recall de MRR@10% do score e dos modelos de comparação

### US-005 — Diretoria recebe ações priorizadas com impacto estimado

Como CEO, quero saber quanto cada ação pode devolver em MRR e como provar que
funcionou, para que eu priorize com dinheiro e não com opinião.

#### AC-015 — O impacto aparece em MRR mensal, com faixa

- **Dado** o risco observado e o risco de referência por idade
- **Quando** o impacto é estimado
- **Então** o excesso de MRR perdido e o valor recuperável em cenários de 25%, 50% e 75% de redução aparecem em dólares por mês

#### AC-016 — O teste A/B proposto tem tamanho de amostra calculado

- **Dado** a taxa de churn do grupo controle, a taxa esperada com a ação, a significância e o poder
- **Quando** o tamanho de amostra é calculado
- **Então** o número por braço bate com a fórmula clássica de duas proporções (0,10 → 0,05 com α 5% e poder 80% dá 435)

### US-006 — Qualquer pessoa reproduz e confere o diagnóstico

Como avaliador, quero rodar um comando e obter exatamente os mesmos números do
relatório, para que eu não precise confiar na palavra de ninguém (nem da IA).

#### AC-017 — Um comando regenera tudo de forma idêntica

- **Dado** os cinco CSVs
- **Quando** o pipeline roda duas vezes
- **Então** `metrics.json` e os CSVs de saída são idênticos byte a byte

#### AC-018 — Os números do relatório conferem com o pipeline

- **Dado** o relatório do CEO com números marcados
- **Quando** o teste de rastreabilidade roda
- **Então** cada número marcado é igual ao valor correspondente em `metrics.json`

## Fora de escopo

- Dashboard web ou API (YAGNI: CSV + relatório + notebook resolvem o uso de amanhã).
- Estimar efeito causal de intervenções com os dados observacionais — não há
  variação exógena; a entrega é o desenho do experimento que estima esse efeito.
- Modelos de série temporal pesados (TimesFM): o controle estatístico simples
  cobre o monitoramento desta fase.

## Suposições

| ID | Suposição | Status | Resolução |
|---|---|---|---|
| ASM-001 | "Churn" para o CEO = perda de receita recorrente; a métrica principal é churn de MRR por assinatura (não o `churn_flag` da conta) | confirmada | As três definições do dataset discordam (AC-004); a de assinatura é a única com datas internamente consistentes (`end_date ≥ start_date` em 100%). Decisão registrada no relatório. |
| ASM-002 | A data de extração dos dados é 2024-12-31 (último dia observado em todas as tabelas) | confirmada | Máximo de todas as colunas de data = 2024-12-31. |
| ASM-003 | O `end_date` das assinaturas representa a data real de saída | invalidada | O tempo até o churn é uniforme na janela observada e a fração que "já churnou" é ~10% em toda coorte, observada 38 ou 670 dias. Tratado como limitação central (US-001) e usado com ressalva. |
| ASM-004 | Uso e tickets estão ligados ao ciclo de vida do cliente | invalidada | 77% do uso é anterior ao início da assinatura e 54% dos tickets são anteriores ao cadastro. Janelas "pré-churn" com esses dados seriam ruído; o diagnóstico usa agregados e registra o problema. |
| ASM-005 | O CEO (não técnico) prefere relatório curto com números marcados a um notebook | confirmada | Guia de submissão: "documento de 40 páginas onde 5 resolveriam" é fraco. Notebook fica como apêndice técnico. |

## Perguntas em aberto

| ID | Pergunta | Status | Resposta |
|---|---|---|---|
| Q-001 | O que mudou em set–out/2024 (campanha de vendas, preço, onboarding)? As assinaturas iniciadas quase dobraram no 4º tri e o churn dos primeiros 60 dias quadruplicou. | aberta | — Pergunta para o CEO/Vendas; é o candidato a quase-experimento. |
| Q-002 | Quem é dono da definição oficial de churn e da instrumentação de eventos? | aberta | — Pré-requisito da recomendação nº 1 do relatório. |
