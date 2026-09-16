# Contrato de dados — o que falta para destravar as features bloqueadas

**Para:** Engenharia de Dados da RavenStack · **De:** AI Master ·
**Relacionado a:** ação 3 do relatório (definição única de churn e
instrumentação), ASM-003, ASM-004, ASM-010 e ao princípio P-009.

Este documento não reclama dos dados: ele lista, item por item, **o campo que
falta** e **o teste que prova que o problema acabou**. Enquanto o teste não
passar, o item continua fora do modelo — é a regra P-009.

Um teste automático (`tests/test_timeline.py`) garante que toda feature
bloqueada no registro (`features.REFERENCE_FEATURES`) aparece aqui. Se alguém
bloquear mais alguma coisa e esquecer de pedir o dado, a suíte quebra.

## 1. Itens bloqueados e o que destrava cada um

| Item bloqueado | Por que está bloqueado | Campo que falta | Teste de aceitação |
|---|---|---|---|
| `auto_renew_share` | `auto_renew_flag` é o estado na extração, sem data: não dá para dizer que valia antes do corte | `subscription_events(subscription_id, event_type='auto_renew_on'/'auto_renew_off', event_at, actor, source)` | Toda assinatura com renovação automática hoje tem pelo menos um evento com data; 0 flags sem evento correspondente |
| `upgrade_share` | `upgrade_flag` idem | `subscription_events(event_type='upgrade', event_at, old_plan, new_plan)` | 100% das assinaturas com `upgrade_flag` verdadeiro têm evento datado; a soma dos eventos reproduz a flag |
| `downgrade_share` | `downgrade_flag` idem | `subscription_events(event_type='downgrade', event_at, old_plan, new_plan)` | Idem para downgrade |
| `commercial_contraction_flag` | Derivada das duas anteriores | Os dois eventos acima | Passa quando `upgrade_share` e `downgrade_share` passarem |
| `usage_trend_ratio_90d` | 76,6% do uso tem data fora da janela da assinatura | Correção da origem de `feature_usage.usage_date` **ou** a chave correta de assinatura por evento | < 1% dos eventos de uso fora da janela `[start_date, end_date]` da assinatura ligada |
| `days_since_last_usage` | Idem | Idem | Idem |

## 2. Itens que não bloqueiam features, mas comprometem a leitura

| Problema | Campo que falta | Teste de aceitação |
|---|---|---|
| Três definições de churn discordam em 80% das contas (Q-002) | Uma definição oficial publicada + `churn_events` ligado à assinatura que encerrou (`subscription_id`) | As três definições concordam em ≥ 99% das contas |
| `end_date` parece atribuído, não observado (ASM-003) | `cancellation_requested_at`, `effective_end_at` e `source` (billing, CS, sistema) | Em 20 cancelamentos auditados, a data do billing bate com `end_date` em ≥ 80% dos casos (ação 0 do relatório) |
| Atributos de contrato sem histórico (ASM-010) | Histórico versionado de `plan_tier`, `seats`, `mrr_amount`, `billing_frequency` (`valid_from`, `valid_to`) | Para qualquer data passada, é possível reconstruir o estado da assinatura naquele dia |
| 54% dos tickets são anteriores ao cadastro da conta | Correção da chave `account_id` em `support_tickets` ou da data de cadastro | < 1% dos tickets com `submitted_at` anterior ao `signup_date` da conta |
| IDs de uso colidem (21 casos) | `usage_id` com espaço suficiente (UUID) | 0 IDs repetidos com conteúdo diferente |

## 3. Ordem sugerida

1. **`end_date` e a definição de churn** (itens da seção 2): decidem se o achado
   central do relatório é real. Custo baixo, impacto máximo.
2. **Linha do tempo do uso**: destrava duas features e todo o time de produto
   volta a poder medir adoção. Medição de hoje sugere ganho pequeno para o
   modelo (§8.7 da matriz de features) — o valor está em product analytics.
3. **Eventos de assinatura com data**: destrava três features e a derivada, e
   permite medir expansão e contração de verdade.

## 4. O que muda quando cada teste passar

Cada item destravado volta ao ciclo normal: entra no registro como
implementada, é medido na triagem univariada com correção de Holm e só entra no
score se mostrar sinal fora do tempo. Nenhum item volta "por decreto".
