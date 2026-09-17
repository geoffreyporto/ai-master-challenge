# Spec: Cenário de ROI

> feature: cenario-roi
> status: em-implementacao

## Contexto

O Diretor quer ROI em horas/mês. Como o arquivo não tem tempos utilizáveis, o
cenário combina números medidos (cobertura e precisão da política) com
premissas explícitas que ele pode trocar.

## Histórias

### US-008 — O Diretor vê quantas horas por mês a automação economiza e de onde vem cada número

Como Diretor de Operações, quero horas e custo economizados por mês com cada
premissa visível, para trocar pelos números reais da operação.

#### AC-023 — Cada parâmetro declara sua origem

- **Dado** o arquivo `assumptions.yaml`
- **Quando** o cenário é carregado
- **Então** cada parâmetro tem valor e origem (`readme`, `medido` ou `premissa`), e toda premissa aponta a pergunta aberta que a substituirá

#### AC-024 — As horas líquidas descontam o retrabalho dos erros da IA

- **Dado** a cobertura e a precisão medidas no hold-out
- **Quando** o cenário é calculado nas faixas baixa, base e alta
- **Então** o resultado mostra horas de triagem poupadas, horas de retrabalho criadas pelos erros automáticos, horas líquidas e custo líquido por mês
- **E** o valor da faixa base é consistente com a fórmula aplicada aos números medidos

## Fora de escopo

- Custo de infraestrutura (o roteador roda em CPU local; custo marginal ≈ 0).

## Suposições

| ID | Suposição | Status | Resolução |
|---|---|---|---|
| ASM-007 | 3 min de triagem manual por ticket, 15 min de retrabalho por roteamento errado, R$ 60/h de custo carregado | aberta | Premissas de mercado sem fonte da empresa; substituídas quando Q-003 for respondida. |

## Perguntas em aberto

| ID | Pergunta | Status | Resposta |
|---|---|---|---|
| Q-003 | Qual o volume mensal real, o tempo de triagem por ticket e o custo/hora carregado do time? | aberta | Estrutura completa em `docs/04-perguntas-em-aberto.md`. Decisão na ausência: 30.000/ano do README + ASM-007. |
