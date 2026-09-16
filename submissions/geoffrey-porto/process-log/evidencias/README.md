# Evidências de execução

Transcrições **reais** de comandos desta entrega, gravadas com a saída do
terminal (não são capturas de tela; são os comandos e o que eles imprimiram).
Todas são reproduzíveis: `cd solution && uv run pytest`.

| Arquivo | O que prova |
|---|---|
| `01-suite-de-testes.log` | A suíte inteira passando |
| `02-gate-onp-spec.log` | 39/39 critérios de aceite com prova PASS e o `audit --ci` apontando só as 3 perguntas em aberto do dono do produto |
| `03-mutacao-do-relatorio.log` | O teste de rastreabilidade pegando um número editado à mão no relatório (`3,20` contra `2,82` do pipeline) e voltando a passar depois de desfeita a edição |
| `04-validacao-fora-do-tempo.log` | O GBM com as 5 tabelas indo de 1,00 no treino para 0,53 fora do tempo, enquanto a idade da assinatura mantém 0,59 |
| `05-efeito-causal-dml.log` | Os dois casos de uso de DML com intervalo de confiança e efeito mínimo detectável |

Capturas de tela do IDE, se o avaliador preferir esse formato, ficam por conta
do candidato — estas evidências cobrem o mesmo conteúdo em texto verificável.
