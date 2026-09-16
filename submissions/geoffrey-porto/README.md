# Submissão — Geoffrey Porto — Challenge 001

## Sobre mim

- **Nome:** Geoffrey Porto
- **LinkedIn:** [linkedin.com/in/geoffreyporto](https://www.linkedin.com/in/geoffreyporto/)
- **Challenge escolhido:** 001 — Diagnóstico de Churn (RavenStack)

---

## Executive Summary

O churn da RavenStack **subiu de verdade, mas só no 4º tri/2024 e só nas
assinaturas novas**: o churn de MRR ficou em <!--m:mrr_churn_ref_avg_pct-->0,83%/mês
até setembro e chegou a <!--m:mrr_churn_dec24_pct-->3,52% em dezembro; ajustando
pelo crescimento da base, o 4º tri teve <!--m:q4_ratio_x-->2,82× as saídas esperadas,
<!--m:young_share_q4_events_pct-->79,6% delas em assinaturas com menos de 90 dias.
É por isso que CS e Produto "não viram": a satisfação não distingue quem sai
(AUC <!--m:csat_auc-->0,52) e o uso total ficou parado enquanto a base cresceu
<!--m:active_subs_growth_x-->5,8×. Nenhum sinal de uso, suporte ou satisfação prevê
o churn (um GBM com as 5 tabelas faz <!--m:oot_gbm_insample_roc-->1,00 no treino e
<!--m:oot_gbm_roc-->0,53 fora do tempo). **Recomendação principal:** antes de
investir, auditar em 1 dia 20 cancelamentos de dezembro no billing — o padrão
também é compatível com datas de cancelamento atribuídas em lote — e, em
seguida, rodar um onboarding D+7/D+30 como teste A/B nas assinaturas novas;
em jogo, US$ <!--m:excess_mrr_per_month_k-->221 mil de MRR por mês acima do normal.

---

## Solução

| Entregável | Onde |
|---|---|
| **Relatório para o CEO** (≤ 5 páginas) | [`solution/RELATORIO.md`](solution/RELATORIO.md) |
| Lista de contas para o CS (50, com motivo e ação) | [`solution/outputs/cs_priority_accounts.csv`](solution/outputs/cs_priority_accounts.csv) |
| Pipeline reprodutível (Python 3.14 + Polars) | [`solution/src/churn_diag/`](solution/src/churn_diag/) |
| Notebook técnico (CRISP-DM, executado) | [`solution/notebooks/diagnostico_churn.ipynb`](solution/notebooks/diagnostico_churn.ipynb) |
| Especificação SDD (2 features: diagnóstico e validação de features) | [`solution/.spec/`](solution/.spec/) |
| Plano de trabalho · Guia · Arquitetura · Matriz de features · Contrato de dados · Casos DML · Referência | [`docs/`](docs/) |

### Abordagem

1. **Regras antes de ferramentas:** separei as perguntas do CEO em descrição
   ("o que aconteceu"), predição ("quem está em risco") e causa ("o que fazer"),
   porque cada uma pede um método diferente.
2. **Auditoria dos dados antes de qualquer gráfico:** a linha do tempo de uso e
   de tickets não conversa com o ciclo de vida do cliente
   (<!--m:usage_before_sub_start_pct-->76,6% do uso antes da assinatura existir), e as
   três definições de churn discordam em <!--m:churn_def_disagree_pct-->80% das contas.
   A unidade de análise virou **assinatura × mês**, a única linha do tempo
   consistente.
3. **Especificação com gate (SDD):** constituição com princípios verificáveis,
   18 critérios de aceite, cada um provado por teste (`onp-spec verify`: 18/18).
4. **Hipóteses testadas, não opiniões:** <!--m:n_hypotheses-->12 hipóteses cruzando
   as 5 tabelas, correção de Holm, invariância (13 perfis de cliente + antes/depois
   da quebra de set–out/2024) e validação fora do tempo.

### Resultados / Findings

- **[Fato]** A alta do 4º tri não é efeito do crescimento da base: saíram
  <!--m:q4_observed_ended-->324 assinaturas contra <!--m:q4_expected_ended-->115 esperadas.
- **[Fato]** O risco de sair no 1º mês foi de <!--m:hz_0_30_ref_pct-->0,95% para
  <!--m:hz_0_30_target_pct-->5,74%; assinaturas maduras ficaram estáveis
  (<!--m:hz_mature_ref_pct-->0,88% → <!--m:hz_mature_target_pct-->1,09%).
- **[Fato]** Esse padrão é **novo**: antes de outubro a razão de risco
  nova/madura era <!--m:hr_before_break_x-->1,2× (sem diferença estatística);
  depois, <!--m:hr_after_break_x-->4,1×. A causa está no que mudou em
  set–out/2024 — pergunta que só a diretoria responde (seção 3 do relatório).
- **[Fato]** CSAT, uso, tickets, motivo declarado, indústria, país, canal e
  plano **não** explicam o churn depois da correção estatística.
- **[Previsão]** Só a idade da assinatura prevê fora do tempo
  (ROC <!--m:oot_age_roc-->0,59); US$ <!--m:expected_loss_90d_k-->518 mil de MRR devem
  sair em 90 dias se o padrão continuar.
- **[Hipótese]** O salto de novas assinaturas no 4º tri trouxe assinaturas que não
  se sustentam — a validar com o teste A/B (<!--m:ab_n_per_arm-->783 por braço).
- **[Hipótese causal]** Com Double Machine Learning (cross-fitting e erro-padrão
  agrupados por conta, sobreposição verificada): cobrança anual não muda o churn
  de forma detectável (<!--m:dml_cobranca_anual_theta-->−0,43 pp, IC
  <!--m:dml_cobranca_anual_ci_low-->−2,01 a <!--m:dml_cobranca_anual_ci_high-->+1,15)
  — intervalo estreito o bastante para descartar desconto por retenção. Já
  escalar ticket é **impossível de responder** com estes dados: só 7 eventos
  entre tratados, efeito mínimo detectável de
  <!--m:dml_escalacao_suporte_mde-->7,4 pp (`docs/06-casos-dml.md`).
- **[Previsão]** As três features de taxa da minha referência de engenharia
  (erros por 100 usos, escalação, CSAT sem resposta) foram medidas e **não têm
  sinal** aqui (<!--m:rates_significant_n-->0 significativas); a replicação do
  desenho por conta reproduz a precisão média publicada
  (<!--m:repl_test_ap-->0,145 contra <!--m:ref_published_ap-->0,144) e mostra que
  idade da conta e idade da assinatura são **sinais distintos** (correlação
  <!--m:age_spearman-->0,32).

### Recomendações

0. Auditar 20 cancelamentos de dezembro no billing (1 dia) — separa "clientes
   saindo" de "defeito de registro".
1. Onboarding D+7/D+30 para assinaturas novas, como teste A/B.
2. CS liga esta semana para as <!--m:cs_top_n-->50 contas da lista
   (US$ <!--m:cs_top_expected_loss_k-->171 mil de MRR em risco).
3. Uma definição única de churn e instrumentação ligada ao ciclo de vida.
4. No board: churn de MRR por idade da assinatura no lugar de CSAT e "uso total".
5. Perguntar a Vendas/Produto/CS o que mudou em set–out/2024 — a pergunta aberta
   que decide a causa (candidato a experimento natural).

### Limitações

Dados sintéticos com linhas do tempo quebradas; três definições de churn em
conflito; nenhum efeito causal provado (não há variação exógena); amostra
pequena na validação (<!--m:oot_positives-->96 saídas). Detalhes na seção 5 do relatório.

---

## Process Log — Como usei IA

> Log completo: [`process-log/PROCESS_LOG.md`](process-log/PROCESS_LOG.md)

### Ferramentas usadas

| Ferramenta | Para que usou |
|---|---|
| Claude Code (Claude Opus 5) | Agente: leitura de regras e método, exploração dos dados, spec, código, testes, relatório |
| onp-spec (Spec-Driven Development) | Gate mecânico: cada critério de aceite provado por teste; audit por exit code |
| uv + Python 3.14 + Polars | Ambiente travado e processamento dos dados |
| pytest + ruff + nbclient | Testes, lint e execução do notebook |

### Workflow

1. Li as regras do desafio e meus documentos de método (CRISP-DM, descrição ×
   predição × causa, invariância, séries temporais, SDD, padrões).
2. Perfil e auditoria dos dados em Polars (~12 sondagens).
3. Especificação: constituição, proposta, 18 critérios, design e tarefas.
4. Implementação com testes, uma tarefa por commit, `verify` a cada etapa.
5. Relatório com números marcados e testados; notebook executado; documentação.

### Onde a IA errou e como corrigi

- A exposição mensal descartava assinaturas que nascem e morrem no mesmo mês —
  justamente o churn precoce (341 de 486 saídas contadas); corrigido, a razão
  do 4º tri foi de 1,95× para 2,82×.
- O rascunho do relatório e o notebook tinham números "de memória" (ex.: 356 em
  vez de 341); o princípio "nenhum número digitado à mão" virou teste e pegou isso.
- A IA marcou como "confirmada" uma suposição que só eu podia confirmar (a
  definição de churn) e como "invalidada" outra que os dados não decidem; as
  duas voltaram para "aberta" até a minha revisão.
- A leitura "churn precoce é a causa raiz" estava confiante demais; o teste de
  coorte mostrou que um defeito de registro produz o mesmo padrão.

### O que eu adicionei que a IA sozinha não faria

O enquadramento (separar descrição, predição e causa; buscar invariância e
quase-experimento) e o processo com gate que obrigou a IA a provar cada número.
No gate, confirmei a definição de churn (com a ressalva de que downgrade não é
cancelamento), mantive as duas perguntas ao CEO abertas e formalizadas em vez
de "passar" o gate, e decidi tratar a quebra de set–out/2024 como ambiente na
análise de invariância — o que revelou que o risco extra das assinaturas novas
**não existia antes de outubro**, mudando a conclusão de "traço do negócio" para
"regime novo com causa a identificar".

---

## Evidências

- [x] Chat export (conversa completa, redigida) — [`process-log/chat-exports/conversa-claude-code.md`](process-log/chat-exports/conversa-claude-code.md)
- [x] Transcrições de execução (comandos e saídas reais) — [`process-log/evidencias/`](process-log/evidencias/)
- [ ] Screenshots — não incluídos de propósito: os mesmos fatos estão em log reproduzível ([`process-log/screenshots/`](process-log/screenshots/) explica)
- [x] Git history — spec primeiro, depois uma tarefa por commit (`T-00X diagnostico-churn: …`)
- [x] Notebook comentado e executado — `solution/notebooks/diagnostico_churn.ipynb`
- [x] Outro: prova mecânica do onp-spec — `solution/.spec/verification/diagnostico-churn.json`

### Como rodar

```bash
cd submissions/geoffrey-porto/solution
uv sync
uv run python -m churn_diag   # regenera outputs/ byte a byte
uv run pytest                 # inclui o teste que confere os números deste README e do relatório
```

Dados: os 5 CSVs do Kaggle ([rivalytics/saas-subscription-and-churn-analytics-dataset](https://www.kaggle.com/datasets/rivalytics/saas-subscription-and-churn-analytics-dataset), MIT, crédito a River @ Rivalytics) em `RAVENSTACK_DATA_DIR` ou em `challenges/data-001-churn/dataset/`.

---

_Submissão enviada em: 14/09/2026_
