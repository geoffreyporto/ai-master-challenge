# Spec: Rascunho de resposta assistido (DeepSeek-V4-Flash)

> feature: rascunho-resposta
> status: em-implementacao

## Contexto

O agente perde tempo escrevendo a primeira resposta. O LLM
`deepseek-ai/DeepSeek-V4-Flash` (Pioneer) redige um rascunho a partir do
ticket mascarado, da fila prevista e dos tickets parecidos. O rascunho nunca é
enviado sozinho: o agente aprova, edita ou descarta.

## Histórias

### US-012 — O agente recebe um rascunho seguro para revisar

Como agente de suporte, quero um rascunho de primeira resposta, para editar
em vez de escrever do zero, sem risco de expor dado de cliente.

#### AC-036 — O rascunho é sempre uma sugestão com contexto

- **Dado** um ticket, sua fila prevista e seus tickets parecidos
- **Quando** o rascunho é gerado
- **Então** o resultado tem status `requer_aprovacao`, o modelo usado, o texto mascarado enviado e o veredito do guardrail
- **E** não existe caminho de código que envie o rascunho ao cliente

#### AC-037 — Rascunhos em amostra real não vazam PII

- **Dado** uma amostra sorteada com semente de tickets do Dataset 1 com nome e e-mail do cliente inseridos
- **Quando** os rascunhos são gerados
- **Então** nenhum rascunho contém o nome ou o e-mail originais
- **E** a taxa de aprovação do guardrail, a latência mediana e os tokens são reportados

## Fora de escopo

- Envio automático ao cliente (proibido pela fronteira).
- Avaliar a qualidade do rascunho contra resposta real (não há resolução real nos datasets).

## Suposições

| ID | Suposição | Status | Resolução |
|---|---|---|---|
| ASM-010 | Um rascunho sem PII e aprovado pelo guardrail é seguro para o agente ler | aberta | Guardrail cobre PII, não correção técnica; o agente continua responsável pelo conteúdo. |

## Perguntas em aberto

Nenhuma além de Q-004 (envio a provedor hospedado), registrada em `privacidade-guardrails`.
