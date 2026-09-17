# Submissão — Geoffrey Porto — Challenge 002

## Sobre mim

- **Nome:** Geoffrey Porto
- **LinkedIn:** [linkedin.com/in/geoffreyporto](https://www.linkedin.com/in/geoffreyporto/)
- **Challenge escolhido:** 002 — Redesign de Suporte

---

## Executive Summary

Antes de responder "onde perdemos tempo", auditei os dados: **o Dataset 1 é
sintético** (`{product_purchased}` literal em <!--m:d1_placeholder_share-->100% das
descrições, categorias uniformes, <!--m:d1_negative_share-->49,3% dos tickets
fechados "resolvidos antes da primeira resposta"), então nenhum gargalo dele pode
virar decisão — e os testes confirmam: nenhuma dimensão move tempo ou CSAT
(menor p = <!--m:d1_min_kw_p-->0,28), com poder para ver diferenças de
<!--m:csat_mde-->0,21 ponto. O que **é** real é o texto do Dataset 2: um
classificador TF-IDF + regressão logística chega a macro-F1
<!--m:b0_macro_f1-->0,867 em <!--m:test_n-->9.568 tickets nunca vistos, e uma
política calibrada roteia sozinha <!--m:coverage_auto-->58,9% dos tickets com
<!--m:precision_auto-->96,6% de precisão, mandando <!--m:human_share-->41,1% para
humano. Os modelos hospedados do Pioneer (GLiNER2 multi-large, DeepSeek-V4-Flash)
ficam muito abaixo no roteamento (macro-F1 <!--m:b2_macro_f1-->0,288 e
<!--m:llm_macro_f1-->0,392) e por isso **não** roteiam; entram onde agregam: rascunho
de resposta com PII mascarada e guardrail (<!--m:draft_leaks-->0 vazamentos).
A recomendação: **piloto de roteamento automático com fronteira medida**
(não 100%), rodando num roteador Rust que decide igual ao modelo avaliado, e
**pedir o export real do help desk** antes de qualquer decisão sobre gargalos.

---

## Solução

### Abordagem

1. **Verificar antes de acreditar.** Os documentos de referência (gerados com IA)
   e o README do challenge foram re-medidos no arquivo. Divergências achadas:
   `Ticket Type` tem 5 valores (README: 3), o arquivo tem
   <!--m:d1_rows-->8.469 linhas (README: ~30.000), e o schema do Pioneer sugerido
   nos docs devolve resposta vazia.
2. **Especificar (SDD / onp-spec).** Constituição com 13 princípios verificáveis
   e 10 features com 41 critérios de aceite em Dado/Quando/Então
   (`solution/.spec/`). Todo teste carrega `@spec:AC-xxx`; `onp-spec verify`
   grava a prova e `onp-spec audit` cruza spec ↔ tarefa ↔ teste ↔ código.
3. **CRISP-DM** para a análise (`docs/CRISP-DM-IT-Support-Challenge.md`), com
   plano de 4–6 h (`docs/01-plano-de-trabalho.md`) e guia
   (`docs/02-guia-de-implementacao.md`).
4. **Construir o mínimo que prova a proposta**: pipeline Python 3.14 + Polars,
   roteador Rust (axum 0.8.9, Rust 1.98.1), app Streamlit. Sem Docker, React ou
   microserviços (`docs/03-arquitetura-e-padroes.md`).

### Resultados / Findings

**1. Diagnóstico operacional — o dado não sustenta gargalo**

| Pergunta do Diretor | Resposta com número | Base |
|---|---|---|
| Os dados são reais? | Dataset 1: sintético (χ² de uniformidade, menor p = <!--m:d1_min_uniform_p-->0,11; e-mails só `example.*`; resoluções 100% únicas e aleatórias). Dataset 2: real, pré-processado (<!--m:d2_rows-->47.837 tickets, 0 duplicatas, desbalanceamento 7,7×) | auditoria |
| Onde o fluxo trava? | Em nenhum segmento de forma detectável: Kruskal-Wallis em canal, prioridade e tipo, menor p = <!--m:d1_min_kw_p-->0,28, ε² ≈ 0 | sintético |
| O que impacta o CSAT? | Nada mensurável: maior diferença entre canais <!--m:csat_max_diff-->0,13 contra <!--m:csat_mde-->0,21 detectável; logit ordinal com pseudo-R² <!--m:csat_pseudo_r2-->0,0010 | sintético |
| Quanto desperdiçamos? | O arquivo **não mede duração** (<!--m:d1_negative_share-->49,3% de intervalos negativos). O desperdício recuperável vem do cenário da seção 4 | lacuna declarada |

O pipeline de diagnóstico está pronto: com o export real (Q-001), os mesmos
testes rodam sem mudar código.

**2. Classificação de tickets (Dataset 2, hold-out de <!--m:test_n-->9.568)**

| Modelo | Macro-F1 | Latência | Observação |
|---|---|---|---|
| B0 TF-IDF (uni+bigramas) + regressão logística, local | <!--m:b0_macro_f1-->0,867 | ~0,04 ms/ticket | Escolhido **na validação**; ECE <!--m:b0_ece-->0,051 |
| B1 Model2Vec potion-base-8M + regressão logística, local | <!--m:b1_macro_f1-->0,756 | ~0,1 ms/ticket | Texto sem stopwords tira o valor do embedding; usado na busca de similares |
| B2 `fastino/gliner2-multi-large-v1` → fallback `fastino/gliner2-large-v1`, zero-shot (Pioneer) | <!--m:b2_macro_f1-->0,288 | ~0,1 s no servidor, ~1 s no cliente | Acurácia <!--m:b2_accuracy-->0,311; o multi-large se absteve (`null`) em parte dos tickets e o fallback atendeu <!--m:b2_fallback-->2.090; <!--m:b2_unanswered-->638 ficaram sem resposta dos dois (contados como erro) |

Na amostra estratificada de <!--m:llm_n-->400 tickets (50 por fila, sorteados com
semente): **B3 `deepseek-ai/DeepSeek-V4-Flash`** como classificador chega a
macro-F1 <!--m:llm_macro_f1-->0,392 (~3 s por ticket), contra
<!--m:llm_b0_macro_f1-->0,888 do B0 e <!--m:llm_b2_macro_f1-->0,282 do GLiNER2 na
mesma amostra. Conclusão: com texto pré-processado (sem gramática nem
stopwords), modelo supervisionado pequeno vence zero-shot grande por larga
margem — o roteamento fica local; os modelos hospedados ganham outro papel
(abaixo).

A fila mais fraca é *Administrative rights* (F1 0,79); a mais forte, *Purchase* (0,92).

**3. O que automatizar — e o que não**

A política (limiar por fila na validação, precisão-alvo 95%, conjunto conformal
com α = 5%, guarda de domínio) roteia <!--m:coverage_auto-->58,9% dos tickets com
<!--m:precision_auto-->96,6% de precisão no hold-out; a cobertura conformal fica em
<!--m:conformal_coverage-->95,0%.

| Automatizar | Não automatizar (e por quê) |
|---|---|
| Classificar e rotear quando a fila tem limiar viável e a confiança passa dele | **Conjunto conformal com 2+ filas** — ex. real: "access to create purchase requests…" (Purchase × Access) |
| Sugerir tickets parecidos já tratados (Recall@5 <!--m:recall_at_5-->92,8% contra <!--m:chance_at_5-->60,3% por sorteio) | **`Miscellaneous`** (15% do volume): fila de sobra, pedidos como "pending approval… approve please report" não têm dono óbvio |
| Normalizar e mascarar o texto antes de qualquer modelo | **Prioridade Critical**: a IA pode rotear, o humano confirma |
| Detectar ticket fora do domínio e desviar | **Resolver**: conceder acesso/direitos, reembolso, cancelamento e resposta ao cliente — rotear não é resolver |
| | **Confiança abaixo do limiar** — ex.: "decommission assets…" (Hardware, 0,659 < 0,678) |

Exemplos sorteados com semente (não escolhidos) estão em
`solution/outputs/metrics.json → boundary.human_examples` e na aba *Fronteira* do app.

**Cruzamento dos datasets.** Aplicado aos <!--m:d1_rows-->8.469 tickets de
eletrônicos do Dataset 1 (domínio que o modelo nunca viu), o roteador manda
<!--m:d1_human_share-->95,1% para humano e só <!--m:d1_auto_share-->3,7% seguem
automáticos (KS p < 0,001 entre as confianças). Sem o guarda de domínio, 18,4%
desses tickets teriam sido roteados para filas de TI — achado que só apareceu ao
cruzar os dois datasets e que virou regra da política.

**Fluxo proposto:** ticket → normalização → classificador local → (conjunto
conformal tem 1 fila? fila tem limiar? confiança ≥ limiar? texto do domínio?)
→ automático / confirmação (Critical) / triagem humana → workspace do agente
com tickets parecidos → máscara de PII → rascunho do LLM → guardrail → agente
revisa e resolve → correção vira rótulo de retreino.
Diagrama em `docs/03-arquitetura-e-padroes.md`.

**Busca de similares.** Recall@1 <!--m:recall_at_1-->75,4%, Recall@5
<!--m:recall_at_5-->92,8%. Limite honesto: as resoluções do Dataset 1 são sintéticas e o Dataset 2
não tem resolução — o Recall@k mede a fila, não a qualidade da resposta.

**Segunda opinião do GLiNER2 — testada e recusada.** Quando o modelo local
manda um ticket para humano só por incerteza, a concordância com o GLiNER2
poderia liberá-lo. Na validação essa concordância acerta só
<!--m:so_val_precision-->69,8% (meta: 95%), então a regra fica **desligada**; no
teste ela acertaria <!--m:so_test_precision-->65,4% em
<!--m:so_test_extra-->5,7% dos tickets — teria trocado triagem por retrabalho.

**Rascunho de resposta com privacidade (Pioneer).** Para os tickets que chegam
ao agente: `fastino/gliner2-privacy-filter-PII-multi` mascara a PII →
`deepseek-ai/DeepSeek-V4-Flash` redige o rascunho a partir do texto mascarado,
da fila e dos tickets parecidos → `fastino/gliguard-PII-multi` barra rascunho
com PII. O rascunho sempre sai como `requer_aprovacao`; não existe caminho de envio.

| Medição (amostra do Dataset 1 com nome e e-mail do cliente inseridos) | Resultado |
|---|---|
| Recall da máscara, nomes / e-mails (n = <!--m:pii_n-->200) | <!--m:pii_name_recall-->100,0% / <!--m:pii_email_recall-->100,0% |
| Rascunhos com nome ou e-mail original (n = <!--m:draft_n-->30) | <!--m:draft_leaks-->0 |
| Rascunhos aprovados pelo guardrail | <!--m:draft_guard_pass-->96,7% (o bloqueado é falso positivo: "please") |
| Latência mediana por rascunho (máscara + LLM + guardrail) | ~3 s |

O guardrail precisou de três iterações, todas registradas: 0% de aprovação (ele
marcava o nosso próprio `[PERSON]`), 16,7% (o prompt pedia "a specialist will
confirm" e ele marcava "specialist" como pessoa), 56,7% (marcava o pronome
"you"). Corrigi o parser e o prompt — não afrouxei o limiar do guardrail.

**4. ROI (cenário, premissas em `solution/assumptions.yaml`)**

| Faixa | Horas líquidas/mês |
|---|---|
| Baixa | <!--m:roi_net_hours_low-->41 |
| Base (2.500 tickets/mês, 3 min de triagem, 15 min de retrabalho, R$ 60/h) | <!--m:roi_net_hours_base-->61 |
| Alta | <!--m:roi_net_hours_high-->102 |

Na faixa base: R$ <!--m:roi_net_brl_year_base-->44.050 por ano, **já descontado**
o retrabalho de cada erro automático. É um número modesto de propósito:
cobertura e precisão são medidas; tempo de triagem e custo/hora são premissas
(Q-002, Q-003). O ganho maior provável — tempo até a primeira atribuição e
reaproveitamento de solução — precisa do export real para ser medido.

**5. Protótipo rodando**

- `solution/app/streamlit_app.py`: Diagnóstico com filtros, Roteador (sorteia
  ticket do hold-out, mostra fila, confiança, ação, motivo e similares),
  Fronteira, Similares e ROI com premissas ajustáveis.
- `solution/router/`: `POST /route` e `GET /health` em Rust, com binários
  prontos em `router/dist/` para macOS, Linux e Windows (o avaliador não precisa
  de Rust; o app sobe o roteador sozinho).
- Testes: 76 no total — unitários, de contrato, paridade Python ↔ Rust e 8
  testes funcionais **E2E com Playwright** no Chrome real (abas, filtro, ticket
  sorteado com decisão do Rust, Critical nunca automático, rascunho do Pioneer,
  busca de similares e ROI), que também geram as capturas de tela. Decide igual ao
  Python em **todos** os <!--m:test_n-->9.568 tickets do hold-out (diferença
  máxima de probabilidade < 1e-15), recusa entrada vazia/grande/inválida sem
  cair, lints `unwrap`/`panic`/`todo` proibidos.

```bash
cd solution
kaggle datasets download -d suraj520/customer-support-ticket-dataset -p data --unzip
kaggle datasets download -d adisongoh/it-service-ticket-classification-dataset -p data --unzip
uv sync && uv run python -m support_redesign        # ~1 min
uv run streamlit run app/streamlit_app.py            # já sobe o roteador Rust pré-compilado
uv run python -m support_redesign.router_bin         # só o roteador, :8080 — sem Rust instalado
uv run pytest                                        # inclui cargo test (este precisa de Rust 1.98.1)
```

### Recomendações

1. **Pedir o export real do help desk** (timestamps por estado, agente,
   reaberturas) e rodar o mesmo pipeline — só então falar de gargalo (Q-001).
2. **Piloto de 4 semanas do roteamento automático local** com a fronteira
   medida, auditando por amostra a precisão dos automáticos por fila. Não usar
   zero-shot hospedado para rotear (macro-F1 <!--m:b2_macro_f1-->0,288).
3. **Piloto do rascunho assistido** (máscara → LLM → guardrail) na fila humana,
   condicionado à resposta do DPO sobre o provedor (Q-004).
4. **Definir com a coordenação o custo de um roteamento errado** e a
   precisão mínima aceita (Q-002) — isso move o limiar e a cobertura.
5. **Nunca automatizar a resolução** de acesso, direitos, reembolso ou resposta
   ao cliente; a IA sugere, o humano decide.
6. **Fechar o ciclo**: correção do agente vira rótulo; retreino e recalibração mensais.

### Limitações

- O diagnóstico operacional é resultado nulo sobre dado sintético; não há
  gargalo real a reportar sem Q-001.
- O ROI depende de três premissas sem fonte da empresa (Q-003).
- Rótulos do Dataset 2 não foram revisados por humano; documentos curtos e
  ambíguos limitam o teto de acurácia.
- GLiNER2 fine-tuned (LoRA) não foi treinado: o Pioneer só aceita upload de
  dataset pelo dashboard; os números hospedados são zero-shot.
- **GLiFormer não foi usado.** O catálogo do Pioneer (consultado em
  `GET /base-models`) só oferece GLiNER2, GLiGuard e o filtro de PII; rodar o
  `knowledgator/gliformer-large-v1` localmente exigiria PyTorch e não entraria
  no roteador. Pelo resultado do GLiNER2 zero-shot (macro-F1 0,288 contra 0,867
  do modelo local), a expectativa é que ele também não roteasse bem este texto
  pré-processado.
- O filtro de privacidade hospedado **vê o texto bruto**; usar em produção
  depende de contrato/DPA com o provedor (Q-004). Rascunhos foram avaliados em
  30 tickets, sem medir a qualidade técnica da resposta.
- A prioridade do Dataset 1 é aleatória, então não houve modelo de triagem de urgência.
- Roteador sem autenticação (protótipo local); requisitos de produção em `docs/03`.

---

## Process Log — Como usei IA

> Detalhes em [`process-log/PROCESS_LOG.md`](process-log/PROCESS_LOG.md).

### Ferramentas usadas

| Ferramenta | Para que usou |
|------------|--------------|
| Claude Code (Opus 5) | Leitura das regras e referências, verificação dos dados, specs onp-spec, código Python/Rust, testes, README |
| Claude (chat) | Documentos de referência: CRISP-DM, guia analítico, stack GLiNER2 |
| onp-spec | Gate mecânico: spec ↔ tarefas ↔ testes ↔ código ↔ constituição |
| Pioneer API | `gliner2-multi-large-v1` (+ fallback `gliner2-large-v1`) no hold-out inteiro; `DeepSeek-V4-Flash` como classificador e redator; `gliner2-privacy-filter-PII-multi` e `gliguard-PII-multi` para privacidade — sempre `store:false` |

### Workflow

1. Li regras, CONTRIBUTING e guia de submissão; baixei os dados via Kaggle CLI.
2. Pedi à IA para **re-medir** cada afirmação dos documentos de referência antes de escrever spec.
3. Escrevi constituição + 8 features + perguntas de negócio abertas.
4. Implementei por feature, com teste por critério de aceite.
5. Cruzei os datasets, vi o problema de domínio, adicionei o guarda e re-medi.
6. Construí roteador Rust com teste de paridade e o app Streamlit; README com números conferidos por teste.

### Onde a IA errou e como corrigi

- **README do challenge e docs gerados com IA**: `Ticket Type` com 3 valores (são 5), "156 placeholders" (depende do regex), "~30K tickets" (8.469). Corrigido medindo.
- **Schema do Pioneer nos docs** (`multi_label:false, top_k:3`) devolve `categories: []`. Descobri testando variantes; só `{task, labels}` funciona e não há top-k.
- **"GLiFormer talvez esteja no Pioneer"**: não está no catálogo.
- **Abstenção do GLiNER2 multi-large** (`topic_group: null` em ~35% dos tickets) não disparava o fallback, que só tratava erro HTTP; o teste de "zero respostas não reconhecidas" pegou.
- **Guardrail com falsos positivos** (nosso `[PERSON]`, "specialist", "you"): três iterações até 96,7%, sem baixar o limiar.
- **A primeira política roteava 18,4% de tickets de outro domínio** — a IA não previu; o cruzamento mostrou e virou regra.
- **Vazamento de chave**: ao inspecionar o `.env` para ler só os nomes, o regex de máscara esperava `=` e o arquivo usava `:` — a chave apareceu no log. Chave marcada para rotação; o código só lê chave de variável de ambiente/arquivo fora do repo.
- **Streamlit**: widget com `key` ignora `value=` novo; o botão "sortear" não trocava o texto. Pego pelo teste do app.
- **Pioneer lento** (~4 s por chamada sem keep-alive): cache em blocos para não perder progresso.

### O que eu adicionei que a IA sozinha não faria

- Tratar o dataset sintético como **achado** para o Diretor, não como obstáculo.
- **Rotear ≠ resolver**: a fronteira humana está na resolução, não só na confiança.
- Guarda de domínio a partir do cruzamento dos datasets.
- Manter as perguntas de negócio **abertas** com dono e decisão na ausência, em vez de inventar números.
- Exigir paridade Python ↔ Rust no hold-out inteiro antes de chamar o roteador de "pronto".

---

## Evidências

- [x] Screenshots — `process-log/screenshots/`: 8 capturas geradas pelos testes E2E (Playwright + Chrome) do app rodando, incluindo o rascunho real do Pioneer
- [x] Chat export — `process-log/chat-exports/`: sessão do Claude Code em Markdown legível + transcript completo (`.jsonl.gz`), com chave e e-mail redigidos
- [x] Narrativa — [`process-log/PROCESS_LOG.md`](process-log/PROCESS_LOG.md)
- [x] Arquitetura — [`docs/05-arquitetura-solucao.html`](docs/05-arquitetura-solucao.html) (Archify, validada e checada em navegador)
- [x] Grafo do código — [`docs/grafo-codigo/`](docs/grafo-codigo/README.md) (graphify: 504 nós, sem ciclos de import)
- [x] Provas do onp-spec em `solution/.spec/verification/` e números em `solution/outputs/metrics.json`

---

_Submissão enviada em: 2026-09-16_
