# Stack técnica e práticas de desenvolvimento

> Inventário completo do que foi usado para produzir esta entrega: linguagem,
> bibliotecas, ferramentas de qualidade, metodologia e o ferramental de
> compressão de contexto. Versões conferidas na máquina de execução, não
> copiadas de memória.
>
> As práticas de engenharia (SDD, SOLID, KISS, DRY, YAGNI, AI-SDLC) têm o
> detalhamento com exemplos de código em
> [`03-arquitetura-padroes-e-sdd.md`](03-arquitetura-padroes-e-sdd.md). Aqui
> está o inventário e a justificativa de cada escolha.

---

## 1. Runtime e bibliotecas

| Camada | Ferramenta | Versão | Por que esta |
|---|---|---|---|
| Linguagem | **Python** | 3.14.0 | Exigência do desafio. Trouxe uma consequência real — ver §5. |
| DataFrame | **Polars** | 1.44.2 | Exigência do desafio. API de expressões deixa a regra de negócio declarativa e testável isoladamente (ex.: `age_bucket_expr()`, `period_expr()`). Execução *lazy* e sem índice evita a classe de bug de `pandas` com junção por índice implícito. |
| Numérico | **NumPy** | 2.5.3 | Álgebra dos estimadores: sanduíche clusterizado do DML, enumeração de coalizões de Shapley. |
| Estatística | **SciPy** | 1.18.1 | Teste exato de Poisson, Mann-Whitney, qui-quadrado, intervalos de confiança. |
| Modelagem | **scikit-learn** | 1.9.1 | `HistGradientBoostingClassifier/Regressor` e `LogisticRegression` nos aprendizados incômodos do DML; `GroupKFold` para *cross-fitting* agrupado por conta. |
| Gráficos | **Matplotlib** | 3.11.2 | Sem camada extra. As 10 figuras saem de `figures.py` + `explainability.py` com paleta e rótulos em pt-BR próprios. |
| Notebook | **ipykernel / nbclient / nbformat** | 6.29 / 0.10 / 5.10 | Notebook executado de ponta a ponta como evidência, com *kernelspec* fixado (`churn-diag`) para não depender do ambiente do avaliador. |

### Camada de apresentação (painéis)

| Camada | Ferramenta | Versão | Por que esta |
|---|---|---|---|
| Lógica da página | **TypeScript** (`tsc`) | 5.x | Tipa o contrato do payload: se `churn_diag.dashboards` mudar o formato, a compilação acusa antes do navegador. Compila para `app.js` versionado — a página abre sem build. |
| Estilo | **Tailwind CSS** 3.4 + **CSS3** próprio | 3.4.17 | Tailwind para o layout; CSS3 para o que ele não cobre sem build (gradiente de fundo, `font-feature-settings: tnum`, regras de impressão). |
| Gráficos | **D3.js** | 7.9 | Controle sobre escala e eixo — barra sempre começa em zero, série temporal mostra o eixo inteiro. |
| Distribuição | `vendor/` local | — | `d3` e `tailwind` vendorizados (671 KB): a página funciona offline, por `file://`, sem CDN. |

Detalhes e leitura dos painéis em
[`10-paineis-por-stakeholder.md`](10-paineis-por-stakeholder.md).

**O que deliberadamente não entrou:** `pandas` (a stack é Polars, misturar as
duas duplicaria a regra), `seaborn` (dependência inteira para um *heatmap* de 8
linhas), `xgboost`/`lightgbm` (o GBM da `scikit-learn` já empata com o acaso
fora do tempo — trocar de biblioteca não compra sinal que não existe),
`statsmodels` (o DML precisa de erro-padrão clusterizado com *cross-fitting*,
que escrevi explícito para poder testá-lo), e `shap` — ver §5.

## 2. Ambiente, build e qualidade

| Função | Ferramenta | Versão | Nota |
|---|---|---|---|
| Gestor de pacotes e venv | **uv** | 0.12.13 | `uv.lock` versionado: o avaliador reproduz byte a byte com `uv sync`. Resolve em segundos, o que importa num desafio de 4 horas. |
| Build backend | **hatchling** | — | Pacote instalável (`src/churn_diag`), não uma pasta de scripts. Importável pelo notebook e pelos testes sem gambiarra de `sys.path`. |
| Lint + formatação | **ruff** | 0.16.7 | Regras `I, F, E, W, PL, B, UP` — inclui complexidade (`PL`) e *bugbear* (`B`). Linha 88. |
| Testes | **pytest** | 9.1.1 | 78 testes. Etiquetas `@spec:AC-xxx` e `@principle:P-xxx` nas *docstrings* ligam cada teste ao critério que ele prova. |
| Ponte de verificação | **TAP** (plugin próprio em `conftest.py`) | — | Converte a saída do pytest em TAP para o *gate* do onp-spec ler prova por critério. |
| Spec-driven | **onp-spec** | — | `verify` + `audit --ci`. Constituição com princípios `P-xxx`, cada `[DEVE]` com verificação executável. |
| Versionamento | **git** | — | 46 commits, um por tarefa (`T-0XX <feature>: …`). O histórico é parte da evidência. |

### Portões que rodam antes de qualquer "pronto"

```bash
uv run ruff check . && uv run ruff format --check .
uv run pytest -q                      # 78 testes, inclui o de rastreabilidade
onp-spec verify && onp-spec audit --ci
uv run python -m churn_diag           # regenera outputs/ de forma determinística
```

O portão de rastreabilidade merece destaque porque é o antídoto específico
contra alucinação de número: todo valor citado em documento é uma marca
`<!--m:chave-->valor` conferida contra `outputs/metrics.json` **recalculado no
próprio teste**. Se o pipeline mudar e o texto não, a suíte falha. O portão foi
testado por mutação (alterei um número de propósito e confirmei que quebra).
Hoje ele cobre cinco documentos: `RELATORIO.md`, `README.md`,
`04-matriz-de-features.md`, `06-casos-dml.md` e `07-perguntas-incomodas.md`.

## 3. Metodologia

| Prática | Onde está | Evidência |
|---|---|---|
| **CRISP-DM** | As seis fases estruturam o plano de trabalho e os commits | [`01-plano-de-trabalho.md`](01-plano-de-trabalho.md) |
| **SDD / OpenSpec + onp-spec** | 7 *features* com `proposal` / `spec` / `tasks`; US-xxx → AC-xxx → T-xxx → teste | `solution/.spec/`, [`03-…`](03-arquitetura-padroes-e-sdd.md) |
| **SOLID** | Um módulo por responsabilidade; `Scorer` como `Protocol` (aberto a extensão, fechado a modificação); `Tables`/`Settings` congelados | [`03-… §3`](03-arquitetura-padroes-e-sdd.md) |
| **KISS** | O score de produção é `risco da faixa × MRR` — conferível na mão pelo CS | `risk.py`, `explainability.py` |
| **DRY** | Regra de negócio em expressão reutilizável (`age_bucket_expr`), não repetida por consulta | `metrics.py` |
| **YAGNI** | Sem API, sem banco, sem orquestrador. Saída é CSV + PNG + JSON | `outputs/` |
| **AI-SDLC** | A IA propõe; o *gate* mecânico decide. Erros da IA registrados com a correção ao lado | [`../process-log/PROCESS_LOG.md`](../process-log/PROCESS_LOG.md) |
| **Desenvolvimento seguro** | Sem rede no pipeline, sem `eval`/`pickle`, dados fora do git, contrato de dados que valida dtype na entrada, `SEED` fixo | `loader.py`, [`05-contrato-de-dados.md`](05-contrato-de-dados.md) |
| **Métodos causais** | ICP-lite (invariância entre ambientes) antes do DML; DML com *cross-fitting* agrupado, SE clusterizado e verificação de sobreposição obrigatória | [`06-casos-dml.md`](06-casos-dml.md) |
| **Séries temporais** | Carta de controle, decomposição por coorte, validação **fora do tempo** (nunca *k-fold* aleatório em dado com tempo) | `metrics.py`, `risk.py` |

## 4. Ferramental de compressão e economia de tokens

O desafio é de IA aplicada; o custo de contexto é parte da engenharia. O que foi
usado, com números reais:

| Ferramenta | Versão | Papel | Efeito medido |
|---|---|---|---|
| **rtk** (Rust Token Killer) | 0.42.0 | Proxy de CLI acionado por *hook*: reescreve `git status` → `rtk git status`, `grep` → `rtk grep` etc., filtrando a saída antes de ela entrar no contexto | Contador global da máquina: **72,8 M de tokens poupados em 7.610 comandos (94,1%)**. O maior ganho isolado é `rtk grep` (997 chamadas, 55,3 M). Overhead de latência: 63 ms médios no `grep`. |
| **graphify** | 0.9.32 | Grafo de código para navegação por caminho/vizinhança em vez de leitura integral de arquivos | **Instalado, não usado nesta entrega.** O pacote tem 16 módulos; a navegação direta cabia no contexto. Registro aqui para não dar a entender que o grafo sustentou alguma conclusão. |
| **archify** | — | — | **Não instalado nesta máquina.** Não foi usado. |
| Compressão manual de contexto | — | Saídas longas resumidas para `outputs/*.csv` e lidas por consulta pontual, em vez de despejadas na conversa | Efeito colateral útil: a mesma disciplina produziu os artefatos que o avaliador consome. |

**Ressalva honesta sobre os números do rtk:** `rtk gain` reporta o contador
global da máquina, não um recorte deste projeto — a ferramenta não segmenta por
repositório. O percentual (94,1%) é representativo do padrão de uso; o valor
absoluto inclui trabalho de outros projetos. Preferi expor a limitação a
apresentar um número que parece mais preciso do que é.

## 5. A restrição do Python 3.14 e o que ela custou

Vale registrar porque afetou uma decisão técnica visível no relatório.

A biblioteca `shap` — padrão de fato para explicabilidade — depende de `numba`,
que ainda não suporta Python 3.14 (`Cannot install on Python version 3.14.0`).
Havia duas saídas: rebaixar o Python, violando o enunciado, ou resolver o
problema. Escolhi a segunda: os valores de Shapley são calculados **exatos**,
por enumeração das 2⁸ = 256 coalizões, com função de valor intervencional
(`explainability.py`).

O resultado ficou melhor que o plano A. A `shap` usaria aproximação para modelo
genérico; a enumeração exata fecha a identidade `Σφᵢ + base = f(x)` com erro de
2,9 × 10⁻¹⁷ — e isso virou teste (`AC-040`). Uma dependência a menos, uma
garantia a mais. A restrição vale até 12 variáveis, onde o custo dobra a cada
variável adicional; o módulo recusa explicitamente acima disso, em vez de
degradar em silêncio.

## 6. Reprodução completa

```bash
cd submissions/geoffrey-porto/solution
uv sync                                  # instala a partir do uv.lock
export CHURN_DATA_DIR=/caminho/para/o/dataset
uv run python -m churn_diag              # regenera outputs/ (métricas, CSVs, 10 figuras)
uv run pytest -q                         # 78 testes
```

O pipeline é determinístico: `SEED = 42`, sem rede, sem relógio. Duas execuções
produzem `metrics.json` idêntico byte a byte — é isso que permite ao teste de
rastreabilidade comparar o documento com o pipeline recalculado.
