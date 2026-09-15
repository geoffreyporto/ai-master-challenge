# Guia de implementação e arsenal analítico

Derivado do *Guia de Implementação e Arsenal Analítico — Churn* (referência do
candidato), **ajustado ao que os dados realmente permitem**. A diferença entre
um guia genérico e este é a coluna "evidência": cada técnica foi usada ou
descartada por um número deste dataset, não por gosto.

## 1. Rodar em 3 comandos

Pré-requisitos: [`uv`](https://docs.astral.sh/uv/) e Python 3.14 (o `uv` instala
se faltar). Dados: os 5 CSVs do Kaggle
([rivalytics/saas-subscription-and-churn-analytics-dataset](https://www.kaggle.com/datasets/rivalytics/saas-subscription-and-churn-analytics-dataset), licença MIT, crédito: River @ Rivalytics).

```bash
cd submissions/geoffrey-porto/solution
uv sync                                   # ambiente travado pelo uv.lock
uv run python -m churn_diag               # gera outputs/ (≈10 s)
uv run pytest                             # suíte completa, inclusive a do relatório
```

O pipeline procura os CSVs em `--data-dir`, depois em `RAVENSTACK_DATA_DIR`,
depois em `solution/data/` e por fim em `challenges/data-001-churn/dataset/` do
fork. Checagens de engenharia:

```bash
uv run ruff check src tests && uv run ruff format --check src tests
node <skill onp-spec>/scripts/onp-spec.mjs verify diagnostico-churn
node <skill onp-spec>/scripts/onp-spec.mjs audit --ci
```

Checksums SHA-256 dos CSVs usados (para conferir que o dado é o mesmo):

| Arquivo | SHA-256 |
|---|---|
| `ravenstack_accounts.csv` | `348d8ba906b7776894b5236b2e7aa91a503d41670dbc9aad30c37b503c9abef5` |
| `ravenstack_subscriptions.csv` | `dcf1d93ca9a35e0dcba0ab686d255f0e9ec26512970bbf0944cf19cbef2d751a` |
| `ravenstack_feature_usage.csv` | `c081da2be8caf987d07f0f79ceb0619aba523d819529230ed6df77984fa21d4e` |
| `ravenstack_support_tickets.csv` | `ba0006951479771ee9f93c98789c96bc5fec892cf11f867afb28194f0b76d220` |
| `ravenstack_churn_events.csv` | `6391c41d8291b7b4845ec9a84d3837c2ed230a33a32a854ec33d4e66dc150940` |

## 2. Roteiro por fase (o que foi feito e onde está)

| Fase CRISP-DM | O que fazer | Onde no código |
|---|---|---|
| 1. Negócio | Separar descrição / predição / causal; métrica = MRR retido | `hypotheses.py` (`ClaimType`), constituição P-004 |
| 2. Dados | Contrato de schema; auditoria de linha do tempo; 3 definições de churn; plausibilidade das coortes | `loader.py`, `quality.py` |
| 3. Preparação | Painel assinatura × mês (única linha do tempo consistente); duas visões: base no 1º dia (taxa) e ativa no mês (risco por idade) | `metrics.exposure_panel` |
| 4. Modelagem | Taxa mensal; risco por idade; padronização de mix; controle 3σ; hipóteses H1–H12 com Holm; invariância; score de perda esperada | `metrics.py`, `hypotheses.py`, `risk.py` |
| 5. Avaliação | Validação fora do tempo (treino jul/24 → teste out/24) contra logística e GBM com as 5 tabelas | `risk.oot_validation` |
| 6. Implantação | Lista do CS; impacto em MRR com cenários; tamanho de amostra A/B; monitoramento | `risk.cs_priority_list`, `impact.py`, notebook §6 |

## 3. Arsenal analítico — usado vs. descartado (com evidência)

| Técnica (guia de referência) | Decisão | Evidência neste dataset |
|---|---|---|
| Análise de coorte | **Usada** | Revelou que a coorte de 38 dias já perdeu 10,1%, igual à de 407 dias (11%) → alerta sobre `end_date` |
| Estratificação (Paradoxo de Simpson) | **Usada** — no uso e no próprio churn | Uso plano em todos os planos (sem reversão); no churn, a padronização por idade mostrou 2,82× o esperado → não é só mix |
| Sobrevivência (Kaplan-Meier / Cox) | **Usada na forma discreta** (risco mensal por faixa de idade) | Mesmo conteúdo do KM por faixa, legível pelo CEO; Cox dispensado: nenhuma covariável além da idade tem sinal |
| LightGBM/GBM ponderado por MRR | **Testado e rejeitado como principal** | ROC 1,00 no treino → 0,52 fora do tempo: decora ruído |
| Regressão logística (baseline) | **Testada** | 0,53 fora do tempo — mesma conclusão |
| SHAP | **Não usado** | Explicar um modelo sem sinal é explicar ruído com gráfico bonito |
| SMOTE-NC | **Descartado** | Sobreamostrar classe minoritária não cria sinal que não existe |
| Isolation Forest | **Desnecessário** | As anomalias relevantes são determinísticas (datas fora do ciclo de vida) e foram contadas exatamente |
| Propensity Score Matching (escalação) | **Descartado** | Escalação não tem associação com churn (AUC ~0,5); confusor latente (encaixe do produto) invalida o casamento |
| Causal Forest / Uplift (T/X-learner) | **Adiado para depois do A/B** | Sem variação exógena nos dados; o teste A/B proposto gera exatamente o dado que esses métodos exigem |
| ICP / IRM (invariância) | **ICP em versão enxuta** | Razão de risco jovem/madura > 1 em 13/13 ambientes; IRM completo sem poder com ~500 contas |
| Quase-experimento / DiD | **Buscado** | Quebra estrutural detectada em out/2024 (controle 3σ); o evento de negócio por trás é a pergunta Q-001 |
| Janelas 30/60/90 dias antes do churn | **Descartado** | 77% do uso é anterior à assinatura; 54% dos tickets anteriores ao cadastro → a janela seria ruído |
| TimesFM / suavização exponencial | **Substituído por controle 3σ** (YAGNI) | O controle simples já detectou a quebra; modelo temporal pesado sem dado confiável não agrega |
| PR-AUC, lift@k, recall de MRR@k | **Usadas** | Acurácia seria enganosa com 4,1% de base |

## 4. Validação — por que não K-fold aleatório

O CEO reclama justamente de uma **mudança no tempo**; K-fold aleatório mistura
passado e futuro e mede otimismo. A validação treina num corte (T0 = jul/24),
testa no seguinte (T0 = out/24) e o teste `test_oot_panel_never_sees_the_future`
apaga todos os eventos ≥ T0 e exige que nenhuma variável mude (P-002).

## 5. Como estender sem quebrar (OCP)

- **Nova hipótese:** escreva `def h13_x(ctx: Context) -> Finding` em
  `hypotheses.py` e acrescente em `REGISTRY`. O Holm passa a considerá-la
  automaticamente; o teste AC-010 exige o rótulo.
- **Novo score:** qualquer classe com `name`, `fit(panel)` e `score(panel)`
  (protocolo `Scorer`) entra em `oot_validation(scorers=[...])`.
- **Novo número no relatório:** adicione a chave em `pipeline.analyse` e use
  `<!--m:chave-->valor` no `RELATORIO.md` — o teste confere sozinho.

## 6. Problemas comuns

| Sintoma | Causa | Solução |
|---|---|---|
| `CSVs da RavenStack não encontrados` | dados não baixados | `export RAVENSTACK_DATA_DIR=/caminho/dos/csvs` |
| `SchemaContractError: tabela 'x': coluna(s) ausente(s)` | versão diferente do dataset | conferir os checksums acima |
| `outputs/metrics.json desatualizado` no teste | código mudou e o pipeline não rodou | `uv run python -m churn_diag` |
| `git status` não mostra a pasta `submissions/` | o `.gitignore` do fork ignora `submissions/` | `git add -f submissions/<nome>` |
