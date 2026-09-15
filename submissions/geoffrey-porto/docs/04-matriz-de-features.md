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

## 2. Desenho dos dois painéis

| Dimensão | Referência | Este projeto |
|---|---|---|
| Unidade | Conta (`account_id`), snapshots mensais | Assinatura paga ativa no corte T0 |
| Janela das features | 90 dias antes de `t0` | Todo o histórico anterior a T0 (sem janela) |
| Horizonte do rótulo | 30 dias | 92 dias |
| Rótulo | Churn da conta (fonte não especificada) | Assinatura encerrada (`end_date`) em [T0, T0+92d) — definição confirmada pelo dono do produto (ASM-001) |
| Validação | Holdout mais recente | Treino com corte 01/07/2024 → teste com corte 01/10/2024 |
| Resultado | ROC-AUC 0,604 · PR-AUC 0,144 | Idade sozinha: ROC <!--m:oot_age_roc-->0,59; logística com tudo: <!--m:oot_logit_roc-->0,53; GBM: <!--m:oot_gbm_roc-->0,52 (<!--m:oot_gbm_insample_roc-->1,00 no treino); base de <!--m:oot_base_rate_pct-->4,1% de saídas |

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
| 6 | `auto_renew_share` | Subscriptions | `auto_renew_flag` | 🟡 | Flag da assinatura | Benchmark. **Flag sem data** (ver seção 7) |
| 7 | `upgrade_share` | Subscriptions | `upgrade_flag` | 🟡 | Flag da assinatura | Benchmark. **Sem data: "medir antes de t0" não é verificável** |
| 8 | `downgrade_share` | Subscriptions | `downgrade_flag` | 🟡 | Flag da assinatura | Benchmark. Mesmo problema de data |
| 9 | `active_seats` | Subscriptions | `seats` (assinatura) + `acct_seats` (conta) | 🟡 | Não é soma de assentos ativos | Benchmark |
| 10 | `usage_total_90d` | Feature usage | `u_count` | 🟡 | Todo o histórico, não 90 dias | Benchmark. Uso total mensal ficou parado em 2024; por assinatura ativa caiu <!--m:usage_change_per_sub_pct-->−83,2% (H4) |
| 11 | `usage_trend_ratio_90d` | Feature usage | — | ❌ | Descartada | Tendência dentro da janela mediria datas desalinhadas (uso antes da assinatura) |
| 12 | `days_since_last_usage` | Feature usage | — | ❌ | Descartada | Mesmo motivo; há uso registrado até depois do fim da assinatura |
| 13 | `feature_breadth_90d` | Feature usage | `u_breadth` | 🟡 | Todo o histórico | Benchmark |
| 14 | `usage_duration_90d` | Feature usage | — | ❌ | Não usada | — |
| 15 | `errors_per_100_uses_90d` | Feature usage | `u_errors` | 🟡 | **Contagem bruta, não taxa** | Benchmark. É o 2º sinal da referência — lacuna a testar aqui |
| 16 | `beta_usage_share_90d` | Feature usage | `u_beta_share` | 🟡 | Todo o histórico | Benchmark |
| 17 | `tickets_90d` | Support | `t_n` (por conta) | 🟡 | Todo o histórico | Benchmark |
| 18 | `escalation_rate_90d` | Support | `t_esc` | 🟡 | Contagem, não taxa | Benchmark. Quem declarou "suporte" como motivo não teve mais atrito (AUC <!--m:support_reason_auc-->0,50, H6) |
| 19 | `response_time_p90_90d` | Support | `t_frt` | 🟡 | Média, não p90 | Benchmark |
| 20 | `satisfaction_missing_share_90d` | Support | `t_csat_missing` | 🟡 | Binária (conta sem nenhuma nota), não proporção | <!--m:csat_missing_pct-->41,2% dos tickets sem nota; o CSAT médio não separa quem sai (AUC <!--m:csat_auc-->0,52, H3) |

Contagem: ✅ 2 · 🟡 14 · ❌ 4.

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
| `commercial_contraction_flag` | ❌ | Depende de `downgrade_share` e `auto_renew_share`, que são flags sem data — risco de vazamento |

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
| `upgrade_flag`, `downgrade_flag`, `auto_renew_flag` (sem data) | Usados como features (7, 8, 6) | **Usados no benchmark** | **Não garantido** — lacuna dos dois projetos: sem data, não há como provar que são anteriores a T0 |

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

## 9. Próxima iteração recomendada

1. **Trocar contagens por taxas** (`errors_per_100_uses`, `escalation_rate`,
   `satisfaction_missing_share`) e testar uma a uma fora do tempo — é o ponto em
   que a referência tem sinal e este projeto ainda não mediu.
2. **Rodar o painel também por conta** (unidade da referência) para ver se
   `tenure_days` é o mesmo efeito da idade da assinatura.
3. **Pôr as flags sem data em quarentena** (`upgrade`, `downgrade`,
   `auto_renew`) até existir data do evento — nos dois projetos.
4. **Janelas de 90 dias, tendência e recência de uso só depois de corrigir a
   instrumentação** (ação 3 do relatório); antes disso, medem datas erradas.
5. `usage_per_active_seat` e o índice de atrito entram na mesma rodada que o item 4.
