# Process log — como a IA foi usada

Registro factual da sessão de trabalho. Os erros listados aqui aconteceram de
verdade nesta sessão e as correções estão no histórico do git e nos testes.

## Ferramentas

| Ferramenta | Para quê |
|---|---|
| **Claude Code (Claude Opus 5, app desktop)** | Agente principal: leitura das regras e da metodologia, exploração dos dados, especificação, código, testes, relatório |
| **onp-spec** (motor Node embarcado na skill, repositório `sdd` do candidato) | Gate mecânico: constituição, critério→teste, `verify`, `audit --ci` |
| **uv + Python 3.14 + Polars 1.44** | Ambiente travado (`uv.lock`) e processamento de dados |
| **pytest + ruff** | Testes (unitários, integração, rastreabilidade do relatório) e lint (I, F, E, W, PL, PT, B, UP) |
| **nbclient** | Executar o notebook de ponta a ponta (sem células com erro) |
| **git** | 1 tarefa = 1 commit (`T-00X diagnostico-churn: …`) |

## Como o problema foi decomposto antes de codar

O candidato entrou com um pacote de contexto próprio, e é esse pacote que dá
direção à IA — não o contrário:

1. **Regras do jogo:** README, guia de submissão, CONTRIBUTING, template.
2. **Método de análise:** CRISP-DM aplicado ao desafio; o documento
   *Data Science Tasks* (descrição × predição × causal); *Relação de Causalidade
   com Previsão* (ICP/IRM e a busca por quase-experimento); *Séries temporais*
   (uso só em monitoramento).
3. **Método de engenharia:** SDD (OpenSpec + onp-spec), padrões (SOLID, KISS,
   DRY, YAGNI), configuração Python (ruff, pytest) — documentos de autoria do
   candidato.
4. **Restrições:** Python 3.14, Polars, notebook; PR-only; só a pasta própria.

A IA leu tudo isso **antes** de abrir os dados, e cada decisão do plano cita a
fonte (ver `docs/01-plano-de-trabalho.md`).

## Workflow (em ordem)

1. **Regras e armadilhas do repositório.** Descobri que o `.gitignore` do fork
   ignora `submissions/` — um `git add` comum geraria um PR vazio. Solução:
   `git add -f` só na pasta própria; o dataset copiado para `challenges/` fica
   fora do commit (regra: não alterar nada fora da pasta).
2. **Perfil dos dados (≈12 sondagens em Polars).** Schemas, nulos, datas,
   integridade referencial, e então as perguntas que mudaram o rumo:
   a linha do tempo faz sentido? as definições de churn concordam? o churn
   subiu em taxa ou só em contagem?
3. **Especificação antes do código.** Constituição com princípios verificáveis,
   proposta, 18 critérios Dado/Quando/Então, design e tarefas. Primeiro audit:
   formato válido, tudo vermelho (esperado).
4. **Implementação com testes**, módulo por módulo (loader → quality → metrics →
   hypotheses → risk → impact → pipeline), `verify` gravando prova por critério.
5. **Relatório com números rastreáveis** e teste de mutação no gate.
6. **Notebook executado** como apêndice; documentação; este log.

Iterações: ~12 sondagens exploratórias; 3 rodadas de correção no relatório e
3 execuções do notebook (erros 3–6 abaixo); várias rodadas de lint; commits
atômicos por tarefa. Observação honesta: os commits T-001–T-008 foram
feitos em lote ao fim da implementação (mesmo minuto), um por tarefa — o
horário não reflete a duração de cada tarefa.

## Onde a IA errou e como foi corrigido

| # | Erro | Como foi percebido | Correção |
|---|---|---|---|
| 1 | Na exploração, a exposição mensal considerava só assinaturas ativas no 1º dia do mês. Isso **descartava quem entra e sai no mesmo mês** — exatamente o churn de início de vida | Conferência de totais: o painel contava 341 saídas, o dataset tem 486 | Painel com duas visões (`active_at_start` para a taxa; ativa no mês para o risco). A razão do 4º tri foi de 1,95× para 2,82× |
| 2 | Primeira hipótese para a alta do 4º tri: "é só mudança de mix (a base ficou mais nova)" | Padronização por idade: observado 2,82× o esperado | Hipótese descartada com número; virou o achado H1 |
| 3 | Depois, a leitura "churn de início de vida é a causa raiz" estava confiante demais | Teste de sanidade de coorte: a coorte de 38 dias perdeu o mesmo que a de 407 dias | Relatório apresenta **duas explicações** (colapso real × data atribuída) e a ação 0 (auditoria no billing) para separá-las |
| 4 | Tratei a mediana 0,5 de "tempo até sair ÷ tempo observado" como prova de data atribuída | Revisão do argumento: com risco baixo e constante, esse tempo também sai quase uniforme | Rebaixado a indício de apoio; a evidência central é a coorte |
| 5 | O rascunho do relatório tinha números que não vinham do pipeline ("~96 saídas", "23 testes", "quase dobraram") | Aplicando o próprio princípio P-003 ao texto | Viraram métricas marcadas (`oot_positives`, `starts_q3_24`, `starts_q4_24`) ou saíram do texto |
| 6 | O notebook citava "356 saídas", "1,96×" e "~10% como a coorte de 670 dias" de memória | Conferência contra o código antes de publicar | 341, 1,95× e a comparação correta (407 dias, 11%); a coorte de 670 dias tem 19,4% com n = 31 |
| 7 | A IA marcou a suposição ASM-001 ("churn = MRR de assinatura") como **confirmada** | Regra do onp-spec: só o dono do produto confirma | Voltou para `aberta`, com a evidência registrada — decisão do candidato |
| 8 | Primeira versão do emissor TAP usava hooks do pytest de forma frágil | Revisão do próprio código | Reescrita como plugin registrado (`TapEmitter`) |
| 9 | Gráficos saíram com meses em inglês, decimal com ponto e rótulo sobreposto | Inspeção visual das imagens geradas | Rótulos pt-BR, vírgula decimal, rótulo reposicionado |

## O que foi descartado de propósito (julgamento, não omissão)

- **Janelas 30/60/90 dias antes do churn** (sugeridas no guia de referência):
  77% do uso é anterior à assinatura; seriam ruído com cara de insight.
- **GBM ponderado por MRR como modelo principal:** ROC 1,00 no treino e 0,52
  fora do tempo. É o resultado que uma resposta "cole o brief na IA" tende a
  entregar como sucesso.
- **SMOTE-NC, SHAP, PSM, Causal Forest:** sem sinal para explicar, sem variação
  exógena para identificar efeito (detalhes em `docs/02-guia-de-implementacao.md`).
- **Deduplicar `usage_id`:** 21 IDs colidem com conteúdo diferente; apagar
  eventos reais seria pior que não fazer nada.

## O que o humano trouxe que a IA sozinha não traria

- **O enquadramento do problema:** a exigência de separar descrição, predição e
  causalidade; a busca por quase-experimento; o uso de invariância como teste de
  estabilidade — tudo dos documentos de método do candidato.
- **O processo com gate:** a escolha de SDD com onp-spec, que obrigou a IA a
  provar cada critério com teste — e que pegou a própria IA em números
  inventados (erros 5 e 6).
- **As restrições de stack e de entrega** (Python 3.14, Polars, notebook, PR).
- **As decisões que continuam humanas:** confirmar a definição de churn
  (ASM-001), responder Q-001/Q-002 e aprovar o push e o Pull Request.

## Evidências

- **Git:** `git log main..submission/geoffrey-porto` — spec primeiro, depois
  uma tarefa por commit.
- **Prova mecânica:** `solution/.spec/verification/diagnostico-churn.json`
  (18/18 critérios com PASS).
- **Notebook comentado:** `solution/notebooks/diagnostico_churn.ipynb` (executado).
- **Chat export:** ver `chat-exports/README.md`.
