# Spec: Efeito causal com Double Machine Learning

> feature: efeito-causal-dml
> status: em-implementacao

## Contexto

Estimar o efeito de ações candidatas sobre o churn sem repetir os erros que
fazem um intervalo de confiança parecer estreito quando não é.

## Histórias

### US-014 — Diretoria recebe efeito estimado com intervalo honesto

Como CEO, quero o efeito de uma ação sobre o churn com intervalo de confiança
que respeite a estrutura dos dados, para não financiar uma ação por causa de um
erro-padrão subestimado.

#### AC-035 — O cross-fitting respeita a conta

- **Dado** um painel com várias linhas por conta
- **Quando** o efeito é estimado
- **Então** cada conta pertence a uma única partição do cross-fitting
- **E** nenhuma conta aparece ao mesmo tempo no ajuste e na previsão de uma partição

#### AC-036 — A sobreposição é verificada e o que não tem par é aparado

- **Dado** as probabilidades de tratamento estimadas
- **Quando** o efeito é estimado
- **Então** o resultado traz o mínimo, o máximo e quantas linhas ficaram fora dos limites
- **E** um painel em que o tratamento é previsível quase perfeitamente interrompe com mensagem clara, em vez de devolver um número sem sentido

#### AC-037 — O erro-padrão é agrupado por conta

- **Dado** um painel com forte correlação dentro da conta
- **Quando** o erro-padrão é calculado
- **Então** o valor agrupado é maior que o ingênuo
- **E** com linhas independentes os dois ficam próximos

#### AC-038 — O poder é publicado junto do efeito

- **Dado** o resultado de uma estimativa
- **Quando** ele é exportado
- **Então** saem o efeito, o intervalo de 95%, o número de contas, de tratados e de eventos entre tratados
- **E** sai o efeito mínimo detectável, para distinguir "sem efeito" de "sem poder"

#### AC-039 — A quebra de regime não é misturada no ajuste

- **Dado** que a relação idade → churn muda entre antes e depois de set–out/2024 (1,2× para 4,1×)
- **Quando** um efeito é estimado
- **Então** ou o regime entra como variável de ajuste, ou a estimativa é restrita a um único regime
- **E** o resultado publicado diz qual das duas coisas foi feita

## Fora de escopo

- Efeito do onboarding: não há registro de contato do CS nos dados (contrato).
- Usar campos sem data ou features de linha do tempo como confundidores.
- Transformar a estimativa em recomendação automática: segue valendo o desenho
  de experimento do relatório.

## Suposições

| ID | Suposição | Status | Resolução |
|---|---|---|---|
| ASM-015 | Os confundidores observáveis (tamanho, plano, tempo de casa, indústria, canal, período) bastam para o ajuste | aberta | É a suposição de não-confusão, **indemonstrável com estes dados**: o encaixe do produto é latente e influencia contrato, uso do suporte e saída ao mesmo tempo. Nenhum teste a resolve — é decisão do dono do produto aceitá-la como suposição de trabalho (e aí o resultado vale como evidência, não como prova) ou rejeitá-la (e aí os dois casos viram desenho de experimento). A feature fica em `em-implementacao` até essa decisão. |
| ASM-017 | Um snapshot é do regime "depois" quando a janela do rótulo cai no 4º tri/2024 (corte a partir de 30/09/2024) | confirmada | Alinha com o recorte de teste da referência: 3.392 linhas antes (churn 6,93%) e 854 depois (10,66%). |
| ASM-016 | `billing_frequency` no corte descreve o contrato naquele momento | confirmada | É o mesmo conjunto de campos de ASM-010 (plano, assentos, MRR e **frequência de cobrança**), confirmado pelo dono do produto em 15/09/2026 com a ressalva de que o dataset não tem histórico para provar. Se a instrumentação mostrar que são mutáveis, as duas reabrem juntas. |

## Perguntas em aberto

| ID | Pergunta | Status | Resposta |
|---|---|---|---|
| Q-004 | Com efeito nulo e intervalo estreito para cobrança anual, o desconto por contrato anual continua? | aberta | — Decisão de Financeiro/Vendas depois de ver o número. |
