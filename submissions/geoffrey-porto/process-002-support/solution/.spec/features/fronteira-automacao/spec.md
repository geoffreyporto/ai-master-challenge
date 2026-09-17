# Spec: Fronteira de automação (IA × humano)

> feature: fronteira-automacao
> status: em-implementacao

## Contexto

Automatizar 100% é red flag. A fronteira é medida: cada ticket só é roteado
automaticamente se o modelo estiver confiante o bastante para a fila prevista
atingir a precisão-alvo; o resto vai para triagem humana. Rotear não é
resolver: conceder acesso, reembolsar ou responder ao cliente continuam humanos.

## Histórias

### US-005 — O Diretor sabe quais tickets podem pular a triagem humana e quais nunca podem

Como Diretor de Operações, quero uma política de roteamento com cobertura e
precisão medidas, para automatizar só onde o erro é raro.

#### AC-013 — Os limiares por fila são escolhidos na validação

- **Dado** as probabilidades do modelo na validação e a precisão-alvo
- **Quando** os limiares são calculados
- **Então** cada fila recebe o menor limiar que atinge a precisão-alvo na validação
- **E** a fila que não atinge a meta em nenhum limiar fica marcada como só-humano

#### AC-014 — A política atinge a precisão no hold-out sem automatizar tudo

- **Dado** a política aplicada ao teste
- **Quando** cobertura e precisão são medidas
- **Então** a precisão dos auto-roteados fica a no máximo 2 pontos abaixo da meta
- **E** a cobertura automática é menor que 100% e a fila humana é reportada

#### AC-015 — Casos de risco nunca saem sem humano

- **Dado** um ticket previsto como `Miscellaneous`, ou marcado como `Critical`, ou com conjunto conformal de mais de uma fila
- **Quando** a política decide
- **Então** a ação é `humano` (ou `confirmar` para Critical), com o motivo explícito

#### AC-016 — O conjunto conformal cumpre a cobertura prometida

- **Dado** o nível α do projeto calibrado na validação
- **Quando** os conjuntos de predição são gerados no teste
- **Então** a fila verdadeira está no conjunto em pelo menos 1 − α − 0,02 dos tickets

#### AC-017 — Os exemplos de "não automatizar" são tickets reais sorteados, não escolhidos

- **Dado** a fila humana do teste
- **Quando** os exemplos do relatório são gerados
- **Então** eles são sorteados com a semente do projeto e cada um mostra texto, fila verdadeira, fila prevista, confiança e motivo

#### AC-032 — A segunda opinião do GLiNER2 só entra se provar precisão na validação

- **Dado** os tickets da validação que a política local mandou para humano só por confiança ou conjunto conformal
- **Quando** o GLiNER2 hospedado concorda com a fila local
- **Então** a regra "concordância vira automático" só é ativada se a precisão dessas concordâncias na validação atingir a meta
- **E** no teste são reportadas a cobertura extra e a precisão dessa regra

## Fora de escopo

- Automatizar a resolução (conceder direitos, reembolso, resposta ao cliente).
- Triagem de prioridade por modelo: a prioridade do Dataset 1 é aleatória, não há o que aprender.

## Suposições

| ID | Suposição | Status | Resolução |
|---|---|---|---|
| ASM-004 | Precisão-alvo de 95% no roteamento automático | aberta | Meta usual de triagem; o custo real de um roteamento errado não foi informado (Q-002). |
| ASM-005 | `Miscellaneous` é fila de sobra e não deve receber ticket automático | aberta | Inferido do nome e do F1 da classe; confirmar com o dono da operação. |

## Perguntas em aberto

| ID | Pergunta | Status | Resposta |
|---|---|---|---|
| Q-002 | Quanto custa um ticket roteado para a fila errada (retrabalho, SLA) e qual precisão mínima a operação aceita? | aberta | Estrutura completa em `docs/04-perguntas-em-aberto.md`. Decisão na ausência: meta de 95% (ASM-004). |
