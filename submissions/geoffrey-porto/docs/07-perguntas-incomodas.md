# As perguntas incômodas

> Este documento responde, uma a uma, às cinco perguntas incômodas do desafio,
> aos cinco critérios de avaliação e às cinco considerações. Todo número aqui
> sai de `solution/outputs/metrics.json` e é conferido por teste
> (`tests/test_report.py`) — nenhum foi digitado à mão.

---

## 1. Isso é uma solução ou um problema de verdade?

**É um problema de verdade, e ele não é o que o enunciado sugere.**

O enunciado pede a causa do churn. A resposta honesta tem duas camadas:

1. **O que dá para afirmar:** o churn subiu em taxa, não só em contagem
   (<!--m:mrr_churn_ref_avg_pct-->0,83%/mês de MRR entre jan–set →
   <!--m:mrr_churn_dec24_pct-->3,52% em dez/24), e a alta está concentrada nas
   assinaturas com menos de 30 dias — risco <!--m:hz_0_30_mult_x-->6,0× o das
   maduras. O 4º tri teve <!--m:q4_ratio_x-->2,82× mais saídas do que o mix de
   idade previa.
2. **O que não dá:** *por que* isso começou entre setembro e outubro de 2024. A
   razão de risco das assinaturas novas passou de <!--m:hr_before_break_x-->1,2×
   antes da quebra para <!--m:hr_after_break_x-->4,1× depois. Nenhuma das cinco
   tabelas registra preço, release, mudança de processo, campanha ou
   concorrente. O dado não contém a variável que explica o dado.

**O problema real, portanto, é de instrumentação, e ele é anterior ao churn.**
<!--m:usage_before_sub_start_pct-->76,6% dos eventos de uso têm carimbo de tempo
anterior ao início da assinatura, <!--m:tickets_before_signup_pct-->53,9% dos
tickets são anteriores ao cadastro da conta, e
<!--m:churn_def_disagree_pct-->80% das contas têm as duas definições de churn
(flag e evento) em conflito. Enquanto isso valer, qualquer modelo treinado nesse
histórico está aprendendo o gerador sintético, não o cliente.

**A parte que é solução:** a priorização da fila do CS. Ela não depende de
resolver a pergunta causal — depende só de idade da assinatura e MRR, que são os
dois campos confiáveis.

---

## 2. Alguém entende e age com o que você entregou?

Critério de aceitação que usei: **o CS consegue conferir o número na mão, sem me
chamar.**

- O score de uma conta é `risco da faixa de idade × MRR pago`, somado pelas
  assinaturas ativas. Nada mais. Não há modelo, não há caixa-preta.
- [`outputs/score_explicado.csv`](../solution/outputs/score_explicado.csv) abre
  uma conta da lista linha a linha: assinatura, plano, idade, risco, MRR,
  contribuição. A soma das <!--m:xai_score_subs_n-->10 linhas **é** a perda
  esperada da conta, sem arredondamento intermediário.
- [`outputs/cs_priority_accounts.csv`](../solution/outputs/cs_priority_accounts.csv)
  traz <!--m:cs_top_n-->50 contas com motivo e ação sugerida por linha.
- Regenerar é um comando: `uv run python -m churn_diag`.

**O que eu deliberadamente não entreguei:** um dashboard de "probabilidade de
churn por conta". Com ROC fora do tempo de <!--m:oot_gbm_roc-->0,53, esse número
daria ao CS a sensação de saber, sem o saber. Priorizar por risco × dinheiro é
defensável; prometer quem vai sair, não.

---

## 3. O modelo preditivo de churn funciona?

**Não, e eu medi isso em vez de supor.** Treinei em julho/2024 e testei em
outubro/2024 (validação fora do tempo, sem espiar o futuro),
<!--m:oot_n_test-->2.330 assinaturas, <!--m:oot_positives-->96 saídas:

| Modelo | ROC fora do tempo | MRR capturado nos 10% do topo |
|---|---|---|
| Só idade da assinatura | <!--m:oot_age_roc-->0,59 (p = <!--m:oot_age_p-->0,003) | — |
| GBM com as 5 tabelas | <!--m:oot_gbm_roc-->0,53 | <!--m:oot_gbm_mrr_recall_pct-->10,3% |
| Regressão logística | <!--m:oot_logit_roc-->0,53 | — |
| Ordenar por MRR (sem modelo) | <!--m:oot_mrr_only_roc-->0,52 | <!--m:oot_mrr_only_mrr_recall_pct-->58,2% |
| Perda esperada (o que entreguei) | — | <!--m:oot_expected_loss_mrr_recall_pct-->49% |

O GBM acerta <!--m:oot_gbm_insample_roc-->1,0 no treino e empata com o acaso no
teste: decorou. E note a linha mais desconfortável da tabela — **ordenar por MRR,
sem modelo nenhum, captura mais dinheiro que o GBM**. A diferença para o score de
perda esperada está dentro do ruído de 96 saídas.

**A auditoria por valores de Shapley** (exatos, por enumeração das 256
coalizões — erro de eficiência <!--m:xai_efficiency_error-->0) mostra *por que*:
a contribuição de cada uma das <!--m:xai_features_n-->8 variáveis fica centrada
em zero, a maior delas move o risco em <!--m:xai_top_feature_pp-->1,01 p.p., e
<!--m:xai_sign_flip_n-->3 variáveis **trocam de sinal** entre indústrias. Sinal
que inverte de direção conforme o segmento não é efeito fraco: é ausência de
efeito sendo lida como padrão.

Testei também as features derivadas da referência de engenharia de features:
<!--m:rates_significant_n-->0 das taxas (erros por 100 usos, escalação, tickets
sem nota) e <!--m:derived_significant_n-->0 das derivadas são significativas. E
o caso mais instrutivo: `usage_per_active_seat` parecia ter sinal
(AUC <!--m:derived_usage_per_seat_auc-->0,592), mas o sinal é do **denominador** —
só `1/assentos` dá AUC <!--m:derived_usage_per_seat_inv_seats_auc-->0,601,
enquanto só o numerador dá <!--m:derived_usage_per_seat_numerator_auc-->0,515. A
feature estava medindo tamanho de empresa com nome de engajamento.

**O que funciona:** idade da assinatura, e só. É pouco, mas é verdadeiro — e é
suficiente para ordenar uma fila.

---

## 4. Que automação ou tempo de CS dá para usar?

Três coisas, em ordem de retorno por hora investida:

**a) Priorização automática da fila (pronta, custo zero).** Um comando gera as
<!--m:cs_top_n-->50 contas que concentram US$ <!--m:cs_top_expected_loss_k-->171
mil de perda esperada — <!--m:cs_top_share_of_loss_pct-->33% do total de
US$ <!--m:expected_loss_90d_k-->518 mil projetados para 90 dias. O CS trabalha
uma lista de 50, não de 500.

**b) Gatilho por idade, não por score.** O risco nos primeiros 30 dias é
<!--m:hz_0_30_target_pct-->5,74% ao mês contra <!--m:hz_mature_target_pct-->1,09%
nas maduras. Isso não pede modelo: pede um contato marcado em D+7 e D+21 para
toda assinatura nova acima de um limite de MRR. É automação de calendário.

**c) Um experimento, porque nada acima prova causa.** Dimensionei o teste A/B:
<!--m:ab_n_per_arm-->783 assinaturas por braço para detectar queda de
<!--m:ab_p0_pct-->5,75% para <!--m:ab_p1_pct-->2,87% no churn de 90 dias, o que
leva <!--m:ab_weeks_to_enroll-->11,6 semanas ao ritmo atual de
<!--m:ab_new_paid_subs_month-->586 novas assinaturas pagas por mês. Esse é o
único caminho para transformar "achamos que onboarding ajuda" em número.

**E o que a análise causal já descartou como automação:** rodei DML (com
cross-fitting agrupado por conta e erros-padrão clusterizados) em dois casos.
Nem cobrança anual (efeito <!--m:dml_cobranca_anual_theta-->-0,429 p.p., IC
[<!--m:dml_cobranca_anual_ci_low-->-2,005; <!--m:dml_cobranca_anual_ci_high-->1,147])
nem escalação de suporte (<!--m:dml_escalacao_suporte_theta-->-2,964 p.p., IC
[<!--m:dml_escalacao_suporte_ci_low-->-8,118; <!--m:dml_escalacao_suporte_ci_high-->2,189])
têm efeito detectável: <!--m:dml_significant_n-->0 significativos. A escada de
CATE é plana (amplitude <!--m:cate_spread_pp-->4,61 p.p. contra erro-padrão de
até <!--m:cate_max_se_pp-->4,79 p.p.), então **não há nem um subgrupo a mirar**.
Com o poder disponível, o menor efeito detectável era
<!--m:dml_cobranca_anual_mde-->2,25 p.p. — não é que o efeito seja zero, é que
efeitos menores que isso não caberiam nesta amostra. Isso é resultado útil: não
monte uma automação de migração para anual esperando reter alguém.

---

## 5. Qual análise seria mais relevante e de maior impacto para o negócio?

**A que não consegui fazer com estes dados, e é justamente por isso que é a
resposta:** descobrir *o que mudou entre setembro e outubro de 2024*.

O motivo é de tamanho. A quebra custou US$ <!--m:excess_mrr_q4_k-->662 mil de MRR
excedente no 4º tri (US$ <!--m:excess_mrr_per_month_k-->221 mil/mês). Reverter
metade valeria US$ <!--m:recovery_50_mrr_month_k-->110 mil/mês, ou
US$ <!--m:recovery_50_arr_equiv_k-->1.325 mil de ARR. Nenhuma feature nova,
nenhum modelo melhor chega perto disso — porque o efeito não está nas variáveis
disponíveis, está no evento que não foi registrado.

A análise concreta seria: cruzar a série de churn com um **log de eventos de
negócio** (mudanças de preço, releases, alterações de processo de onboarding e
renovação, campanhas, entradas de concorrente) e rodar um estudo de
interrupção de série temporal. É uma tabela que a RavenStack precisa passar a
ter — não é trabalho de modelagem, é de instrumentação.

**Em segundo lugar:** consertar os carimbos de tempo. Eu medi quanto isso vale
antes de pedir — reconstruí as features de tendência e recência usando só as
contas com linha do tempo consistente, e a AUC sai de
<!--m:timeline_trend_auc_bruto-->0,51 para
<!--m:timeline_trend_auc_consistente-->0,554. Real, mas modesto: consertar
timestamps compra ~4 pontos de AUC, não um modelo bom. Vale fazer pela
confiabilidade, não pela previsão.

---

## Critérios de avaliação

### Rigor analítico

Doze hipóteses pré-registradas, testadas com correção de Holm para comparações
múltiplas: <!--m:n_significant-->2 de <!--m:n_hypotheses-->12 sobrevivem. A
validação é fora do tempo, não por embaralhamento — com dados de churn, validação
cruzada aleatória vaza o futuro. Todo efeito vem com intervalo de confiança, e
os efeitos causais vêm com verificação de sobreposição obrigatória
(<!--m:dml_escalacao_aparados-->626 linhas aparadas por falta de par comparável,
registradas em vez de escondidas). A invariância foi testada em
<!--m:invariance_envs-->13 ambientes: o efeito da idade é positivo em
<!--m:invariance_positive-->13 deles, mas **não é invariante à quebra temporal** —
razão de <!--m:invariance_hr_min_x-->1,9× a <!--m:invariance_hr_max_x-->3,7×.
Por isso a estimação por DML condiciona no regime ou se restringe ao período
pós-quebra; agregar os dois seria somar dois mundos diferentes.

### Pensamento crítico

Está no que foi **descartado**: o composto que media assentos com nome de
engajamento, as <!--m:quarantined_features_n-->3 flags sem data (removidas
porque, sem carimbo de tempo, não dá para provar que descrevem o cliente antes
do corte — e o desempenho não piorou sem elas), e o GBM inteiro. Também está no
registro dos próprios erros: o painel de exposição, na primeira versão, contava
só assinaturas ativas no início do mês e perdia 145 das 486 saídas — o erro está
documentado no log de processo, não apagado do histórico.

### Comunicação

O relatório separa três categorias, marcadas no texto: **[Fato]** (o dado
sustenta), **[Previsão]** (projeção com incerteza) e **hipótese** (não
verificável com estes dados). A seção 3 é inteira sobre o que os dados *não*
respondem. Cada número do relatório é uma marca `<!--m:chave-->valor` conferida
contra `outputs/metrics.json` por teste automatizado — se o pipeline mudar e o
texto não, a suíte quebra. Esse portão foi testado por mutação.

### Uso de IA

O processo inteiro está em `process-log/`: a conversa completa, as transcrições
de execução com comandos e saídas reais, e um commit por tarefa. Os erros que a
IA cometeu no caminho estão listados com a correção ao lado. A metodologia é
spec-driven: cada critério de aceitação tem teste com etiqueta `@spec:AC-xxx`, e
o portão mecânico (`onp-spec audit`) **falha de propósito** enquanto houver
pergunta de negócio em aberto — reescrevê-las para passar seria trocar o
instrumento pela nota.

### Praticidade

O entregável operacional é um CSV de 50 contas com motivo e ação, regenerável
com um comando, mais o dimensionamento do experimento que validaria a ação.

---

## Considerações

### "Cruze uso de features com eventos de churn"

Feito — e o resultado é que **não dá para confiar no cruzamento**.
<!--m:usage_before_sub_start_pct-->76,6% dos eventos de uso são anteriores ao
início da assinatura à qual pertencem, e há <!--m:usage_id_collisions-->21
colisões de identificador. Cruzei mesmo assim, das duas formas: com todo o
histórico e só com as contas de linha do tempo consistente. Nenhuma variável de
uso separa quem sai (<!--m:timeline_significant_n-->0 significativas; tendência
de uso <!--m:timeline_trend_auc_consistente-->0,554, recência
<!--m:timeline_recency_auc_consistente-->0,463 — abaixo de 0,5, ou seja, na
direção contrária). A conclusão é sobre o dado, não sobre o cliente.

### "Veja tickets de suporte: quem saiu abriu mais?"

Não. A relação entre motivo declarado do churn e categoria do ticket é
praticamente nula (V de Cramér <!--m:reason_feedback_cramers_v-->0,065), a
categoria do ticket não separa (AUC <!--m:support_reason_auc-->0,50) e a nota de
satisfação também não (AUC <!--m:csat_auc-->0,52, média
<!--m:csat_mean_2024-->3,97). Some-se que <!--m:csat_missing_pct-->41,2% dos
tickets não têm nota — e testei se *a própria ausência* da nota seria sinal
(hipótese comum e razoável): AUC <!--m:rate_satisfaction_missing_auc_all-->0,50.
Não é. Os motivos de churn estão distribuídos quase uniformemente, de
<!--m:reason_share_min_pct-->15,2% a <!--m:reason_share_max_pct-->19,0% — que é o
que se espera de um sorteio, não de um cliente insatisfeito.

### "'O uso cresceu' vale para todos os segmentos?"

Essa é a armadilha mais fácil do desafio, e a resposta é **não, e nem para a
empresa toda**. O volume total de uso é essencialmente plano
(<!--m:usage_monthly_min-->10.039 a <!--m:usage_monthly_max-->11.450 eventos por
mês, tendência sem significância, p = <!--m:usage_trend_p-->0,88). O que cresceu
foi a **base**: de <!--m:active_subs_jan24-->656 para
<!--m:active_subs_dec24-->3.773 assinaturas ativas,
<!--m:active_subs_growth_x-->5,8×. Uso por assinatura, portanto,
**variou <!--m:usage_change_per_sub_pct-->−83,2%**. Quem olhar o total vai comemorar
crescimento de engajamento enquanto o engajamento individual despenca. E por
segmento: nenhum se separa dos demais depois da correção de Holm
(menor p ajustado <!--m:segments_min_p_holm-->0,30) — o que reforça que o recorte
que importa é idade da assinatura, não perfil de cliente.

### "Nem todo churn pesa igual: US$ 50 e US$ 5.000 não são a mesma perda"

Concordo, e é por isso que **toda a priorização é em dólares, não em contagem**.
A prova de que isso muda a resposta: em contagem, o 4º tri foi
<!--m:q4_ratio_x-->2,82× o esperado; em MRR, <!--m:q4_mrr_ratio_x-->4,16×
(US$ <!--m:q4_mrr_lost_k-->872 mil perdidos contra
US$ <!--m:q4_mrr_expected_k-->209 mil esperados). Quem saiu valia mais que a
média. Por isso a fila do CS ordena por `risco × MRR` e não por risco, e por isso
<!--m:cs_top_n-->50 contas (10% da base) concentram
<!--m:cs_top_share_of_loss_pct-->33% da perda esperada. O mesmo princípio vale
para a validação: reportei *recall de MRR* no topo da fila, não só ROC — porque
acertar 100 contas de US$ 50 não paga o time.

### "Cuidado com conclusões apressadas"

Três vezes em que a conclusão apressada estava disponível e foi recusada:

1. **"O uso caiu, logo o cliente está desengajando."** Caiu por assinatura porque
   a base quintuplicou. Não é comportamento, é aritmética.
2. **"`usage_per_active_seat` prevê churn."** Previa assentos
   (AUC do inverso de assentos <!--m:derived_usage_per_seat_inv_seats_auc-->0,601
   contra <!--m:derived_usage_per_seat_numerator_auc-->0,515 do numerador).
3. **"O GBM tem ROC 1,0."** No treino. Fora do tempo,
   <!--m:oot_gbm_roc-->0,53.

E a conclusão que **não** estou tirando, apesar de ser tentadora: "assinaturas
novas causam churn". Idade prevê; não causa. A causa é o que quer que tenha
mudado entre setembro e outubro de 2024 e que atinge desproporcionalmente quem
acabou de entrar — hipótese que continua aberta, com o experimento já
dimensionado para testá-la.

---

## Referências

- Relatório executivo: [`../solution/RELATORIO.md`](../solution/RELATORIO.md)
- Matriz de features: [`04-matriz-de-features.md`](04-matriz-de-features.md)
- Casos causais: [`06-casos-dml.md`](06-casos-dml.md)
- Métricas cruas: [`../solution/outputs/metrics.json`](../solution/outputs/metrics.json)
