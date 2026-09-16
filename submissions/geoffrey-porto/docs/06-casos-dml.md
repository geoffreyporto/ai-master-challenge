# Dois casos de uso com Double Machine Learning

Fecha o ciclo do desafio: descrição → predição → **efeito estimado de uma ação**.
Aqui não se pergunta "quem vai sair", e sim "**se fizermos X, o churn muda?**".
Números marcados são conferidos por teste contra o pipeline.

## 1. Por que o código da referência precisava de três correções

O documento *AI & Statistic Models — Churn* traz o método certo (score
ortogonal de Neyman + cross-fitting). O código publicado, aplicado a este
painel, produziria intervalos de confiança estreitos demais:

| Defeito | O que acontece neste painel | Correção aplicada |
|---|---|---|
| `KFold(shuffle=True)` | O painel empilha 19 snapshots por conta: a mesma conta cai em treino e validação, e a função auxiliar decora a conta | `GroupKFold` por `account_id` — cada conta em uma única partição (AC-035) |
| Erro-padrão sem agrupamento | Linhas da mesma conta não são independentes: ICC do churn ≈ 0,36 com 9,7 linhas por conta | Sanduíche **agrupado por conta**: soma o score dentro da conta antes de elevar ao quadrado (AC-037) |
| Sobreposição não verificada | Tratados sem par de controle entram na conta como se fossem comparáveis | Checagem obrigatória, aparo em [0,02; 0,98] e contagem publicada; sem par, a estimativa **para** com mensagem (AC-036) |

E uma quarta, apontada na revisão: a relação principal **não é invariante** entre
antes e depois da quebra de set–out/2024 (razão de risco 1,2× → 4,1×). Misturar
os dois regimes é misturar dois mundos. Toda estimativa aqui **ou** leva o regime
como variável de ajuste, **ou** é restrita a um regime — e diz qual (AC-039).

## 2. Caso 1 — Escalar um ticket muda o churn?

**Decisão que resolve:** manter ou não o investimento em escalonamento/SLA como
alavanca de retenção.

| Elemento | Definição |
|---|---|
| Tratamento | Pelo menos um ticket escalado nos 90 dias antes do corte |
| Desfecho | Evento de churn não-reativação em (t₀, t₀+30] |
| População | Conta-mês **com pelo menos um ticket** na janela (sem ticket, o tratamento não existe — não é zero) |
| Ajuste | Tempo de casa, MRR ativo, assentos, nº de assinaturas, idade da assinatura mais nova, volume de tickets, plano, indústria, país, canal, **regime** |
| Fora do ajuste | Uso e satisfação posteriores à escalação (mediadores), tudo de `churn_events` (descendentes do desfecho), campos sem data |

**Resultado:** efeito de <!--m:dml_escalacao_suporte_theta-->−2,96 pontos
percentuais, intervalo de <!--m:dml_escalacao_suporte_ci_low-->−8,12 a
<!--m:dml_escalacao_suporte_ci_high-->+2,19 — **não distinguível de zero**.

**Mas a leitura honesta não é "não tem efeito":** só
<!--m:dml_escalacao_aparados-->626 linhas foram aparadas por falta de
sobreposição e restam 7 eventos de churn entre os tratados. O desenho só
enxergaria diferenças de <!--m:dml_escalacao_suporte_mde-->7,4 pontos
percentuais ou mais. Nenhum processo de suporte muda churn nessa magnitude, então
**esta pergunta não é respondível com os dados de hoje** — e saber disso agora
custa nada, contra semanas de modelagem terminando em dar de ombros.

Para responder de verdade: ampliar a janela do tratamento (escalação em 180
dias), acumular mais snapshots, ou tratar SLA como experimento.

## 3. Caso 2 — Cobrança anual reduz o churn?

**Decisão que resolve:** gastar ou não margem de desconto empurrando clientes do
mensal para o anual.

| Elemento | Definição |
|---|---|
| Tratamento | Maioria das assinaturas ativas em cobrança anual no corte |
| Desfecho | Evento de churn não-reativação em (t₀, t₀+30] |
| População | Todas as conta-mês com assinatura paga ativa |
| Ajuste | Mesmo conjunto do caso 1, sem volume de tickets |
| Sobreposição | 38% tratadas; probabilidade estimada entre 0,06 e 0,95, **nenhuma linha aparada** |

**Resultado:** efeito de <!--m:dml_cobranca_anual_theta-->−0,43 pontos
percentuais, intervalo de <!--m:dml_cobranca_anual_ci_low-->−2,01 a
<!--m:dml_cobranca_anual_ci_high-->+1,15 (p = 0,59). O desenho enxergaria
diferenças a partir de <!--m:dml_cobranca_anual_mde-->2,3 pontos percentuais.

**Aqui "não detectamos efeito" significa alguma coisa:** o intervalo é estreito o
bastante para descartar o ganho que justificaria desconto agressivo. Restringindo
ao regime pós-quebra, o efeito vai a
<!--m:dml_anual_pos_quebra_theta_pp-->−0,14 pp — mesma conclusão, com menos poder.

**Recomendação:** não financiar migração para anual como alavanca de retenção.
Se o desconto existir, que seja justificado por fluxo de caixa, não por retenção
(pergunta Q-004, de Financeiro/Vendas).

## 4. O que nenhum método causal responde aqui

A ação principal do relatório — **contato de onboarding nas assinaturas novas** —
não tem coluna de tratamento em lugar nenhum: não existe registro de contato do
CS. DML não estima o efeito de uma ação que ninguém registrou. É exatamente para
isso que serve o teste A/B desenhado no relatório, e é por isso que o contrato de
dados (`05-contrato-de-dados.md`) pede as tabelas de evento.

## 5. O que este resultado **não** prova

<!--m:dml_significant_n-->0 dos casos deu efeito significativo — e mesmo que
desse, a suposição de não-confusão (ASM-015) é **indemonstrável** com estes
dados: o encaixe do produto é latente e influencia ao mesmo tempo a escolha do
contrato, o uso do suporte e a saída. O que o DML entrega é o melhor ajuste
possível pelo que foi observado, com intervalo honesto — não uma prova causal.
Antes de virar decisão irreversível, cada efeito estimado deveria passar por
análise de sensibilidade (quão forte teria de ser um confundidor não observado
para virar a conclusão) ou por experimento.
