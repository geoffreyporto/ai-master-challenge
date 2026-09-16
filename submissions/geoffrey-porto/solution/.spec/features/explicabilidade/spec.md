# Spec: Explicabilidade como auditoria

> feature: explicabilidade
> status: em-implementacao

## Contexto

Cinco gráficos de explicabilidade, calculados sem a biblioteca `shap` (que não
roda em Python 3.14), usados para auditar um modelo que já sabemos fraco.

## Histórias

### US-015 — Time de dados audita o modelo com gráfico, não com fé

Como time de dados, quero ver a contribuição de cada variável por conta e por
ambiente, para provar se o modelo aprendeu estrutura ou ruído.

#### AC-040 — Os valores de Shapley são exatos

- **Dado** um modelo e um conjunto de variáveis
- **Quando** os valores de Shapley são calculados por enumeração de coalizões
- **Então** a soma das contribuições de cada conta mais o valor base é igual à previsão do modelo para aquela conta
- **E** uma variável que o modelo ignora recebe contribuição zero

#### AC-041 — Os cinco gráficos saem com a leitura de auditoria

- **Dado** o painel fora do tempo
- **Quando** a explicabilidade roda
- **Então** saem os arquivos dos cinco gráficos (beeswarm, dependência, waterfall, heatmap por ambiente e escada de CATE)
- **E** a tabela de apoio traz a contribuição média por variável e por ambiente, com a variação entre ambientes

#### AC-042 — A escada de CATE é avaliada fora da amostra

- **Dado** o efeito heterogêneo estimado
- **Quando** a escada é montada
- **Então** os quantis são formados com o efeito previsto no treino e as médias são calculadas em dados separados
- **E** o resultado diz se há heterogeneidade aproveitável ou se a escada é plana

#### AC-043 — O score de produção se explica sem aproximação

- **Dado** uma conta da lista do CS
- **Quando** a explicação do score é gerada
- **Então** a soma das contribuições por assinatura é exatamente a perda esperada da conta
- **E** cada linha mostra idade, risco da faixa e MRR da assinatura

## Fora de escopo

- Usar as contribuições como evidência causal.
- Instalar `shap` (incompatível com Python 3.14) ou trocar a versão do Python.

## Suposições

| ID | Suposição | Status | Resolução |
|---|---|---|---|
| ASM-018 | 8 variáveis de negócio bastam para a auditoria (2^8 = 256 coalizões, cálculo exato viável) | confirmada | Com mais variáveis o custo dobra a cada uma; as 8 escolhidas cobrem tamanho, tempo de casa, uso e suporte — os grupos que o documento de referência quer auditar. |

## Perguntas em aberto

| ID | Pergunta | Status | Resposta |
|---|---|---|---|
| — | Nenhuma. | — | — |
