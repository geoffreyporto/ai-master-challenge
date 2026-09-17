# Spec: Diagnóstico operacional

> feature: diagnostico-operacional
> status: em-implementacao

## Contexto

O Diretor perguntou onde o fluxo trava, o que impacta a satisfação e quanto
se desperdiça. Com o Dataset 1 sintético, o valor está em rodar os testes
certos, mostrar que não há sinal com poder estatístico para detectá-lo, e
deixar o pipeline pronto para o dado real.

## Histórias

### US-002 — O Diretor vê onde o fluxo trava e o que move o CSAT, com teste e tamanho de efeito

Como Diretor de Operações, quero gargalos e drivers de satisfação medidos por
teste estatístico, para distinguir padrão de acaso.

#### AC-004 — Os segmentos canal × prioridade × tipo são medidos

- **Dado** os tickets fechados do Dataset 1
- **Quando** o diagnóstico roda
- **Então** existe uma tabela com os 80 segmentos (4 canais × 4 prioridades × 5 tipos), com n, mediana do intervalo resposta→resolução e CSAT médio
- **E** o pior segmento é apontado com o rótulo de base `sintetico`

#### AC-005 — Cada dimensão tem teste, tamanho de efeito e poder

- **Dado** os tickets fechados
- **Quando** o diagnóstico testa horas e CSAT por canal, prioridade e tipo
- **Então** cada teste traz p-valor de Kruskal-Wallis e ε²
- **E** a menor diferença de CSAT detectável entre canais (α = 0,05, poder = 0,80) é reportada
- **E** a conclusão "sem driver detectável" só aparece se todos os p-valores forem ≥ 0,05

#### AC-006 — O modelo multivariado de CSAT é reportado

- **Dado** os tickets fechados com CSAT
- **Quando** uma regressão logística ordinal usa canal, prioridade, tipo, idade e horas
- **Então** o pseudo-R² e o p-valor do teste de razão de verossimilhança são reportados

### US-003 — O Diretor sabe o que dá e o que não dá para dizer sobre desperdício

Como Diretor de Operações, quero saber quanto tempo é desperdiçado, e se o
dado não sustenta a conta, quero saber por quê e de onde virá o número.

#### AC-007 — O arquivo não é usado para calcular horas desperdiçadas

- **Dado** a fração de intervalos negativos do Dataset 1
- **Quando** o diagnóstico tenta estimar desperdício
- **Então** o resultado é uma lacuna declarada com o motivo, e o número de desperdício vem de `cenario-roi`
- **E** a composição de status (aberto, pendente, fechado) é reportada como descrição ilustrativa

#### AC-008 — Todo achado declara a base e o tipo de afirmação

- **Dado** a lista de achados do diagnóstico
- **Quando** ela é gerada
- **Então** cada achado tem base (`sintetico` ou `real`) e tipo (`descricao`, `predicao` ou `cenario`)

## Fora de escopo

- Simulação de filas (Erlang C / SimPy): o cenário de ROI cobre a pergunta com menos premissas.
- Qualquer gargalo "encontrado" sem teste significativo.

## Suposições

| ID | Suposição | Status | Resolução |
|---|---|---|---|
| ASM-002 | O intervalo "Time to Resolution − First Response Time" é o tempo de tratamento | aberta | São carimbos de data, não durações; a leitura é a única possível, mas 49% dão negativo — por isso nenhum número de horas vira achado. |

## Perguntas em aberto

Nenhuma além de Q-001 (dado real), registrada em `auditoria-dados`.
