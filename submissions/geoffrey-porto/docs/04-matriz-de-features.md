# Matriz de features — este projeto × *Features Engineering* (referência)

Compara as features de ML usadas neste projeto (`solution/src/churn_diag/risk.py`)
com a proposta do documento *Features Engineering* (20 features, 8 controles,
3 derivadas e exclusões por vazamento). Números marcados `<!--m:…-->` são
conferidos por teste contra `outputs/metrics.json`; os demais citam o arquivo
de origem em `solution/outputs/`.

## 1. Resumo

- **Cobertura:** das 20 features da referência, **15 estão implementadas** (a
  maioria no painel por conta do incremento 2), **3 estão em quarentena** por não
  terem data e **2 foram excluídas** porque dependem da linha do tempo de uso,
  que está quebrada. Os **8 controles** estão todos implementados.
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

Legenda: ✅ implementada (com o painel e a coluna que a implementam) · 🔒 em
quarentena (campo sem data, P-009) · ⛔ excluída pela linha do tempo quebrada ·
⬜ ainda não construída. **O status vem do registro único
`churn_diag.features.REFERENCE_FEATURES`** e um teste confere que toda feature
marcada como implementada aponta uma coluna que existe de verdade no painel —
esta tabela não é mantida à mão.

| # | Feature | Fonte | Onde está aqui | Status | Evidência / motivo |
|---|---|---|---|---|---|
| 1 | `tenure_days` | accounts | painel por conta: `tenure_days` · diagnóstico: `tenure_days` | ✅ | Medida: AUC 0,34 (menor = mais risco), significativa após Holm. É o sinal forte do painel por conta — e **não** é o mesmo que idade da assinatura (§8.3) |
| 2 | `active_mrr` | subscriptions | painel por conta: `active_mrr` | ✅ | Medida: AUC 0,41, significativa após Holm — conta menor sai mais. Também é o peso do score de perda esperada |
| 3 | `plan_tier` | accounts/subscriptions | painel por conta: `plan_tier` · diagnóstico: `plan_tier` | ✅ | H12: sem diferença após Holm |
| 4 | `active_subscriptions` | subscriptions | painel por conta: `active_subscriptions` | ✅ | Não medida isoladamente. Cuidado: mais assinaturas = mais chance de alguma encerrar (exposição, não risco) |
| 5 | `annual_share` | subscriptions | painel por conta: `annual_share` | ✅ | Medida: AUC 0,45, sem significância |
| 6 | `auto_renew_share` | subscriptions | — | 🔒 | Em quarentena (P-009); tirar as três flags não custou desempenho (§8.4) |
| 7 | `upgrade_share` | subscriptions | — | 🔒 | Em quarentena (P-009) |
| 8 | `downgrade_share` | subscriptions | — | 🔒 | Em quarentena (P-009) |
| 9 | `active_seats` | subscriptions | painel por conta: `active_seats` | ✅ | Não medida isoladamente |
| 10 | `usage_total_90d` | feature_usage | painel por conta: `usage_total_90d` | ✅ | Medida: AUC 0,52, sem significância. No agregado, uso parado em 2024 e queda de 83,2% por assinatura ativa (H4) |
| 11 | `usage_trend_ratio_90d` | feature_usage | — | ⛔ | Excluída: 76,6% do uso é anterior ao início da assinatura — a tendência mediria datas erradas |
| 12 | `days_since_last_usage` | feature_usage | — | ⛔ | Excluída pelo mesmo motivo; há uso registrado até depois do fim da assinatura |
| 13 | `feature_breadth_90d` | feature_usage | painel por conta: `feature_breadth_90d` | ✅ | Não medida isoladamente |
| 14 | `usage_duration_90d` | feature_usage | painel por conta: `usage_duration_90d` | ✅ | Não medida isoladamente |
| 15 | `errors_per_100_uses_90d` | feature_usage | painel por conta: `errors_per_100_uses_90d` | ✅ | Medida: AUC 0,525 (90 dias) e 0,528 (histórico) — sem significância (§8.2) |
| 16 | `beta_usage_share_90d` | feature_usage | painel por conta: `beta_usage_share_90d` | ✅ | Não medida isoladamente |
| 17 | `tickets_90d` | support_tickets | painel por conta: `tickets_90d` | ✅ | Medida: AUC 0,51, sem significância |
| 18 | `escalation_rate_90d` | support_tickets | painel por conta: `escalation_rate_90d` | ✅ | Medida: AUC 0,474 (90 dias) e 0,481 (histórico) — sem sinal (§8.2) |
| 19 | `response_time_p90_90d` | support_tickets | painel por conta: `response_time_p90_90d` | ✅ | Não medida isoladamente |
| 20 | `satisfaction_missing_share_90d` | support_tickets | painel por conta: `satisfaction_missing_share_90d` | ✅ | Medida: AUC 0,500 nos dois recortes — nenhum sinal (§8.2) |

## 4. Controles contextuais

A referência usa estes 8 como controles de segmentação e de estabilidade entre
ambientes — o mesmo papel da análise de invariância daqui.

| Controle | Fonte | Onde está aqui | Status | Evidência / motivo |
|---|---|---|---|---|
| `industry` | accounts | painel por conta: `industry` · diagnóstico: `industry` | ✅ | Ambiente da análise de invariância (5 indústrias) e H9 |
| `country` | accounts | painel por conta: `country` · diagnóstico: `country` | ✅ | H10: sem diferença após Holm |
| `referral_source` | accounts | painel por conta: `referral_source` · diagnóstico: `referral_source` | ✅ | Ambiente da invariância (5 canais) e H11 |
| `is_trial` | accounts | painel por conta: `is_trial` | ✅ | No diagnóstico é filtro (trials fora do painel); no painel por conta é coluna |
| `seats` | accounts | painel por conta: `seats` · diagnóstico: `acct_seats` | ✅ | Tamanho declarado da conta |
| `high_priority_ticket_share_90d` | support_tickets | painel por conta: `high_priority_ticket_share_90d` | ✅ | Só no painel por conta |
| `resolution_time_mean_90d` | support_tickets | painel por conta: `resolution_time_mean_90d` | ✅ | Painel por conta em 90 dias; no diagnóstico, `t_res` sobre todo o histórico |
| `satisfaction_mean_90d` | support_tickets | painel por conta: `satisfaction_mean_90d` | ✅ | Medida: AUC 0,55, sem significância. No diagnóstico, `t_csat` (histórico) — H3 |

Resultado da estabilidade aqui: a relação idade → risco se mantém nos
<!--m:invariance_envs-->13 ambientes de perfil (razão entre
<!--m:invariance_hr_min_x-->1,9× e <!--m:invariance_hr_max_x-->3,7×), mas **não no
tempo**: <!--m:hr_before_break_x-->1,2× antes da quebra de set–out/2024 e
<!--m:hr_after_break_x-->4,1× depois. Nenhum segmento difere após Holm (menor p
ajustado <!--m:segments_min_p_holm-->0,30).

## 5. Features derivadas sugeridas pela referência

| Controle | Fonte | Onde está aqui | Status | Evidência / motivo |
|---|---|---|---|---|
| `usage_per_active_seat_90d` | feature_usage/subscriptions | — | ⬜ | Fase B do plano: `usage_total_90d ÷ max(active_seats, 1)` |
| `support_friction_index` | support_tickets | — | ⬜ | Fase B: soma de z-scores ajustados só no treino |
| `commercial_contraction_flag` | subscriptions | — | 🔒 | Bloqueada: depende de duas flags em quarentena |

Cobertura do registro: 23 implementadas · 4 em quarentena · 2 excluídas por linha do tempo · 2 não implementadas (fase B).

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
0,52). A suposição ASM-009 foi confirmada pelo dono do produto: a quarentena é
política permanente, não experimento — dá para ser íntegro sem perder poder.

### 8.5 O ranking da referência × a evidência daqui

A triagem da referência ordenou as features por importância de permutação. Com
as medições acima, o quadro fica assim:

| Top da referência | O que este projeto mostra |
|---|---|
| 1. `tenure_days` | **Confirmado como o sinal mais forte** do painel por conta (AUC 0,34, significativo após Holm) — mas é um sinal **diferente** da idade da assinatura (§8.3) |
| 2. `errors_per_100_uses_90d` | **Medido como taxa:** AUC 0,525 (90 dias) e 0,528 (histórico), sem significância. Na referência, a importância era +0,003 com desvio ±0,004 — ou seja, dentro do ruído lá também |
| 3. `usage_trend_ratio_90d` | Não construída: datas de uso desalinhadas do ciclo de vida |
| 4. `plan_tier` | Sem diferença após Holm (H12) |
| 5. `annual_share` | Medida: AUC 0,45, sem significância |
| 6. `active_seats` | Não medida isoladamente |
| 7. `satisfaction_missing_share_90d` | **Medida:** AUC 0,500 nos dois recortes — nenhum sinal |
| 8. `auto_renew_share` | Em quarentena (campo sem data) |
| 9. `industry` | Sem diferença após Holm (H9); estável como ambiente da invariância |

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
