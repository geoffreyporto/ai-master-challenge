# Matriz de features — este projeto × *Features Engineering* (referência)

Compara as features de ML usadas neste projeto (`solution/src/churn_diag/risk.py`)
com a proposta do documento *Features Engineering* (20 features, 8 controles,
3 derivadas e exclusões por vazamento). Números marcados `<!--m:…-->` são
conferidos por teste contra `outputs/metrics.json`; os demais citam o arquivo
de origem em `solution/outputs/`.

## 1. Resumo

- **Cobertura:** das 20 features da referência, **2 são iguais**, **14 aparecem
  de forma parcial** (outra granularidade, outra janela ou contagem em vez de
  taxa) e **4 não existem aqui**.
- **Os dois desenhos diferem em unidade, janela e rótulo** (tabela 2), então as
  métricas de desempenho não se comparam diretamente.
- **Divergência principal:** a referência se apoia em janelas de 90 dias de uso
  e de tickets. Aqui essas janelas foram descartadas porque
  <!--m:usage_before_sub_start_pct-->76,6% do uso é anterior à assinatura e
  <!--m:tickets_before_signup_pct-->53,9% dos tickets são anteriores ao cadastro
  da conta — a janela mediria datas desalinhadas do ciclo de vida.
- **Convergência:** os dois concluem que o desempenho é modesto e que o ganho
  virá de uma definição melhor de churn, não de um modelo mais complexo.
- **Achado que a referência não tem:** a única variável com sinal fora do tempo
  aqui é a **idade da assinatura** (`age_days`), que não está na lista das 20.
- **Medido depois desta matriz** (feature `validacao-features`, seção 8): as três
  taxas da referência foram calculadas e **nenhuma tem sinal** aqui
  (<!--m:rates_significant_n-->0 significativas após Holm); o desenho da
  referência foi replicado (precisão média <!--m:repl_test_ap-->0,145 contra
  <!--m:ref_published_ap-->0,144 publicados); e idade da conta e idade da
  assinatura **não são o mesmo sinal**.

## 2. Desenho dos dois painéis

| Dimensão | Referência | Este projeto |
|---|---|---|
| Unidade | Conta (`account_id`), snapshots mensais | Assinatura paga ativa no corte T0 |
| Janela das features | 90 dias antes de `t0` | Todo o histórico anterior a T0 (sem janela) |
| Horizonte do rótulo | 30 dias | 92 dias |
| Rótulo | Churn da conta (fonte não especificada) | Assinatura encerrada (`end_date`) em [T0, T0+92d) — definição confirmada pelo dono do produto (ASM-001) |
| Validação | Holdout mais recente | Treino com corte 01/07/2024 → teste com corte 01/10/2024 |
| Resultado | ROC-AUC 0,604 · PR-AUC 0,144 | Idade sozinha: ROC <!--m:oot_age_roc-->0,59; logística com tudo: <!--m:oot_logit_roc-->0,53; GBM: <!--m:oot_gbm_roc-->0,53 (<!--m:oot_gbm_insample_roc-->1,00 no treino); base de <!--m:oot_base_rate_pct-->4,1% de saídas |

PR-AUC depende da taxa base, que a referência não informa — por isso não dá
para comparar 0,144 com o PR-AUC daqui (`oot_validation.csv`).

## 3. Matriz das 20 features

Legenda: ✅ igual · 🟡 parcial · ❌ ausente. "Benchmark" = entra só na logística
e no GBM com todas as tabelas, que empatam com o acaso fora do tempo; nesses
casos não há evidência individual da feature.

| # | Feature (referência) | Fonte | Equivalente aqui | Status | Diferença | Evidência neste projeto |
|---|---|---|---|---|---|---|
| 1 | `tenure_days` | Accounts | `tenure_days` (T0 − `signup_date`) | ✅ | — | Benchmark. O sinal forte aqui é a idade da **assinatura**, não da conta: o "tenure" da referência pode estar capturando o mesmo efeito |
| 2 | `active_mrr` | Subscriptions | `mrr_amount` da assinatura | 🟡 | Por assinatura, não soma por conta | Peso do score de perda esperada. "Só MRR" captura <!--m:oot_mrr_only_mrr_recall_pct-->58,2% do MRR que sai no top 10%; perda esperada, <!--m:oot_expected_loss_mrr_recall_pct-->49% |
| 3 | `plan_tier` | Accounts/Subs | `plan_tier` da assinatura (one-hot) | ✅ | — | H12 (plano inicial da conta): sem diferença após Holm |
| 4 | `active_subscriptions` | Subscriptions | — | ❌ | Unidade é a assinatura | No nível de conta, mais assinaturas = mais chance de "alguma encerrar" (efeito de exposição, não de risco) |
| 5 | `annual_share` | Subscriptions | `billing_frequency` (one-hot) | 🟡 | Categoria da assinatura, não proporção | Benchmark |
| 6 | `auto_renew_share` | Subscriptions | — (quarentena) | ❌ | Flag sem data | **Removida** de todas as matrizes (P-009). Sem ela, os modelos não pioraram (seção 8) |
| 7 | `upgrade_share` | Subscriptions | — (quarentena) | ❌ | Flag sem data | **Removida** (P-009): "medir antes de t0" não é verificável |
| 8 | `downgrade_share` | Subscriptions | — (quarentena) | ❌ | Flag sem data | **Removida** (P-009) |
| 9 | `active_seats` | Subscriptions | `seats` (assinatura) + `acct_seats` (conta) | 🟡 | Não é soma de assentos ativos | Benchmark |
| 10 | `usage_total_90d` | Feature usage | `u_count` | 🟡 | Todo o histórico, não 90 dias | Benchmark. Uso total mensal ficou parado em 2024; por assinatura ativa caiu <!--m:usage_change_per_sub_pct-->−83,2% (H4) |
| 11 | `usage_trend_ratio_90d` | Feature usage | — | ❌ | Descartada | Tendência dentro da janela mediria datas desalinhadas (uso antes da assinatura) |
| 12 | `days_since_last_usage` | Feature usage | — | ❌ | Descartada | Mesmo motivo; há uso registrado até depois do fim da assinatura |
| 13 | `feature_breadth_90d` | Feature usage | `u_breadth` | 🟡 | Todo o histórico | Benchmark |
| 14 | `usage_duration_90d` | Feature usage | — | ❌ | Não usada | — |
| 15 | `errors_per_100_uses_90d` | Feature usage | `errors_per_100_uses` (90d e histórico) | ✅ | — | **Medida:** AUC <!--m:rate_errors_auc_90d-->0,525 (90 dias) e <!--m:rate_errors_auc_all-->0,528 (histórico) — sem significância após Holm |
| 16 | `beta_usage_share_90d` | Feature usage | `u_beta_share` | 🟡 | Todo o histórico | Benchmark |
| 17 | `tickets_90d` | Support | `t_n` (por conta) | 🟡 | Todo o histórico | Benchmark |
| 18 | `escalation_rate_90d` | Support | `escalation_rate` (90d e histórico) | ✅ | — | **Medida:** AUC <!--m:rate_escalation_auc_90d-->0,474 e <!--m:rate_escalation_auc_all-->0,481 — sem sinal; H6 já mostrava atrito igual entre quem declarou "suporte" e os demais |
| 19 | `response_time_p90_90d` | Support | `t_frt` | 🟡 | Média, não p90 | Benchmark |
| 20 | `satisfaction_missing_share_90d` | Support | `satisfaction_missing_share` (90d e histórico) | ✅ | — | **Medida:** AUC <!--m:rate_satisfaction_missing_auc_90d-->0,500 e <!--m:rate_satisfaction_missing_auc_all-->0,500 — nenhum sinal; <!--m:csat_missing_pct-->41,2% dos tickets sem nota |

Contagem depois da medição: ✅ 5 · 🟡 11 · ❌ 4 + 3 em quarentena.

## 4. Controles contextuais

A referência usa estes 8 como controles de segmentação e de estabilidade entre
ambientes — o mesmo papel da análise de invariância daqui.

| Controle (referência) | Aqui | Uso |
|---|---|---|
| `industry` | ✅ feature + ambiente | Invariância (5 indústrias) e H9 |
| `country` | ✅ feature | H10 (sem diferença após Holm) |
| `referral_source` | ✅ feature + ambiente | Invariância (5 canais) e H11 |
| `is_trial` | 🟡 filtro | Trials fora do painel fora do tempo; MRR zero no score |
| `seats` da conta | ✅ `acct_seats` | Benchmark |
| `high_priority_ticket_share_90d` | ❌ | — |
| `resolution_time_mean_90d` | ✅ `t_res` (todo o histórico) | Benchmark |
| `satisfaction_mean_90d` | ✅ `t_csat` (todo o histórico) | H3 |

Resultado da estabilidade aqui: a relação idade → risco se mantém nos
<!--m:invariance_envs-->13 ambientes de perfil (razão entre
<!--m:invariance_hr_min_x-->1,9× e <!--m:invariance_hr_max_x-->3,7×), mas **não no
tempo**: <!--m:hr_before_break_x-->1,2× antes da quebra de set–out/2024 e
<!--m:hr_after_break_x-->4,1× depois. Nenhum segmento difere após Holm (menor p
ajustado <!--m:segments_min_p_holm-->0,30).

## 5. Features derivadas sugeridas pela referência

| Derivada | Aqui | Comentário |
|---|---|---|
| `usage_per_active_seat_90d` | ❌ | Só no agregado (uso por assinatura ativa, H4). Faz sentido depois de corrigir a instrumentação |
| `support_friction_index` | 🟡 | H6 usa "tickets + 2×escalações" para validar o motivo declarado, não como feature e sem z-score |
| `commercial_contraction_flag` | ❌ | Depende de duas flags sem data, agora em quarentena (P-009) — não é construível com integridade |

## 6. Features só deste projeto

| Feature | Por quê |
|---|---|
| `age_days` (idade da assinatura em T0) | **Única com sinal fora do tempo** (ROC <!--m:oot_age_roc-->0,59); base do score de produção (risco por faixa de idade) |
| `mrr_amount` como peso | Score = risco × MRR: ordena pelo dinheiro em jogo |
| `prior_churn_events` | Eventos de churn **anteriores** a T0 — histórico, não descendente do rótulo futuro |
| `billing_frequency`, `country` | Na referência, uma é proporção e a outra é controle |
| Ambiente "período" (antes/depois da quebra) | Decisão do dono do produto (ASM-006); revelou o regime novo |

## 7. Exclusões por vazamento

| Item | Referência | Aqui | Como é garantido aqui |
|---|---|---|---|
| `churn_date`, `reason_code`, `refund_amount_usd`, `feedback_text`, `churn_event_id` | Excluídos | Excluídos | Regex proibida em `risk.py` (P-002) |
| Campos de `churn_events` pós-evento (`preceding_*`) | Excluídos | Excluídos | Mesma regex |
| Qualquer dado ≥ `t0` | Excluído | Excluído | Teste que apaga todos os eventos ≥ T0 e exige features idênticas |
| `accounts.churn_flag`, `subscriptions.churn_flag` / `end_date` | **Não mencionados** | Excluídos | O painel seleciona só as colunas permitidas; teste confere que não aparecem |
| `upgrade_flag`, `downgrade_flag`, `auto_renew_flag` (sem data) | Usados como features (7, 8, 6) | **Em quarentena** | P-009: lista única em `features.QUARANTINED_UNDATED`, regex proibida em `risk.py` e teste que confere a ausência nos dois painéis |

## 8. Triagem da referência × evidência daqui

| Top da referência | O que este projeto mostra |
|---|---|
| 1. `tenure_days` | Não testada isoladamente; a idade da assinatura é o sinal forte daqui |
| 2. `errors_per_100_uses_90d` | Não testada como taxa (só contagem bruta) — lacuna |
| 3. `usage_trend_ratio_90d` | Não usada: datas de uso desalinhadas do ciclo de vida |
| 4. `plan_tier` | Sem diferença após Holm (H12) |
| 5. `annual_share` | Só benchmark |
| 6. `active_seats` | Só benchmark |
| 7. `satisfaction_missing_share_90d` | Só a versão binária; CSAT médio sem sinal (AUC <!--m:csat_auc-->0,52) |
| 8. `auto_renew_share` | Só benchmark; flag sem data |
| 9. `industry` | Sem diferença após Holm (H9); estável como ambiente |

## 8. Resultados medidos (feature `validacao-features`)

Três perguntas abertas por esta matriz foram fechadas com medição. O painel por
conta replica o desenho da referência (conta × fim de mês, janelas de 90 dias,
rótulo = evento de churn não-reativação em 30 dias, treino até 31/08/2024).

### 8.1 A replicação bate com a referência?

| | Referência publicada | Replicação aqui |
|---|---|---|
| Linhas de treino | <!--m:repl_train_rows-->3.392 | <!--m:repl_train_rows-->3.392 |
| Linhas de teste | <!--m:repl_test_rows-->854 | <!--m:repl_test_rows-->854 |
| Taxa de evento no teste | 10,7% | <!--m:repl_test_positive_rate_pct-->10,7% |
| Precisão média (AP) | <!--m:ref_published_ap-->0,144 | <!--m:repl_test_ap-->0,145 |
| ROC-AUC | <!--m:ref_published_roc-->0,604 | <!--m:repl_test_roc-->0,57 |

O painel reproduz **exatamente** o recorte (mesmas linhas e mesmas taxas de
evento) e a precisão média. O ROC fica ~0,03 abaixo porque a replicação roda com
cinco features a menos: as três em quarentena (P-009) e as duas descartadas por
linha do tempo (`usage_trend_ratio_90d`, `days_since_last_usage`).

### 8.2 As três taxas têm sinal?

| Taxa | AUC (janela de 90 dias) | AUC (histórico completo) | Significativa após Holm |
|---|---|---|---|
| `errors_per_100_uses` | <!--m:rate_errors_auc_90d-->0,525 | <!--m:rate_errors_auc_all-->0,528 | não |
| `escalation_rate` | <!--m:rate_escalation_auc_90d-->0,474 | <!--m:rate_escalation_auc_all-->0,481 | não |
| `satisfaction_missing_share` | <!--m:rate_satisfaction_missing_auc_90d-->0,500 | <!--m:rate_satisfaction_missing_auc_all-->0,500 | não |

Nenhuma das três separa quem sai de quem fica (<!--m:rates_significant_n-->0
significativas). Vale para os dois recortes de janela — ou seja, aqui o problema
não é só a janela de 90 dias: as taxas não têm sinal nem sobre todo o histórico.
Detalhe por feature em `outputs/feature_screening.csv`.

### 8.3 Idade da conta e idade da assinatura são o mesmo sinal?

| Medida | Valor |
|---|---|
| Correlação de Spearman entre as duas | <!--m:age_spearman-->0,32 |
| AUC da idade da conta (menor = mais risco) | <!--m:age_auc_tenure-->0,34 |
| AUC da idade da assinatura mais nova | <!--m:age_auc_min_sub-->0,39 |
| ROC do modelo só com idade da conta | <!--m:age_roc_tenure_only-->0,68 |
| ROC do modelo só com idade da assinatura | <!--m:age_roc_sub_only-->0,52 |
| ROC do modelo com as duas | <!--m:age_roc_both-->0,65 |
| Ganho ao juntar | <!--m:age_gain_both-->−0,03 |

**Veredito: sinais distintos.** A correlação é fraca (0,32) e, no painel por
conta com o rótulo de evento de churn, a idade da conta prevê bem melhor que a
idade da assinatura; juntar as duas piora. Ou seja, o `tenure_days` da
referência **não** é o mesmo sinal que a idade da assinatura deste diagnóstico —
são dois efeitos diferentes, cada um no seu par de unidade e rótulo.

**Ressalva:** num painel que empilha snapshots mensais, `tenure_days` também
carrega a coorte de entrada. Como o rótulo dispara no 4º tri/2024, parte desse
poder preditivo pode ser o mesmo regime novo que a pergunta Q-001 investiga —
não uma propriedade estável de contas jovens.

### 8.4 Quanto custou a quarentena?

Tirar as <!--m:quarantined_features_n-->3 flags sem data da matriz do
diagnóstico **não piorou** os modelos fora do tempo: a logística ficou em
<!--m:oot_logit_roc-->0,53 e o GBM em <!--m:oot_gbm_roc-->0,53 (antes, 0,53 e
0,52). A suposição ASM-009 se confirma: dá para ser íntegro sem perder poder.

## 9. Próxima iteração recomendada

1. ~~Trocar contagens por taxas e testar fora do tempo~~ — **feito** (8.2):
   nenhuma das três tem sinal.
2. ~~Rodar o painel também por conta~~ — **feito** (8.1 e 8.3): o desenho
   replica e as duas idades são sinais distintos.
3. ~~Pôr as flags sem data em quarentena~~ — **feito** (8.4), sem custo de
   desempenho.
4. **Janelas de 90 dias, tendência e recência de uso só depois de corrigir a
   instrumentação** (ação 3 do relatório); antes disso, medem datas erradas.
5. `usage_per_active_seat` e o índice de atrito entram na mesma rodada que o item 4.
