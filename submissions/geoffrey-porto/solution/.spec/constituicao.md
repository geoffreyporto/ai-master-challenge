# Constituição — Diagnóstico de Churn RavenStack — v1.0.0

<!--
  Princípios inegociáveis do projeto. Não são estilo: são restrições.
  P-xxx = princípio (código de rastreio, como US/AC/T).
  Níveis: [DEVE] obrigatório · [RECOMENDADO] forte · [PODE] permitido/explícito.
  Todo [DEVE] precisa de verificação executável — senão o audit acusa
  "princípio sem verificação" (PRINCIPIO_SEM_VERIFICACAO). Formatos:
    - verificação(gate): satisfeita pelo próprio audit (só p/ princípios "meta")
    - verificação(teste): @principle:P-xxx
    - verificação(proibido): `regex` em `glob`
    - verificação(obrigatório): `regex` em `glob`
-->

Contexto: um relatório de diagnóstico que um CEO vai usar para decidir onde
gastar dinheiro. O risco principal não é o código quebrar — é **um número
errado ou uma correlação vendida como causa** chegar ao CEO. Os princípios
abaixo existem para tornar esses dois erros mecanicamente detectáveis.

## P-001 [DEVE] Todo requisito tem prova executável

Nenhuma feature é declarada pronta sem o audit em modo CI sair limpo (exit 0).
Verificado pelo próprio mecanismo do audit (AC_SEM_TESTE, AC_SEM_PROVA,
TASK_CONCLUIDA_SEM_PROVA).

- verificação(gate): intrínseca ao audit

## P-002 [DEVE] Nenhum descendente do churn entra no score de risco

`reason_code`, `refund_amount_usd`, `feedback_text` e `churn_date` só existem
DEPOIS que o cliente saiu. Usá-los para prever churn é vazamento de rótulo: o
score fica ótimo no papel e inútil na operação. O módulo de score não pode nem
mencioná-los, e toda feature do painel preditivo usa só dados anteriores ao
corte T0.

- verificação(proibido): `reason_code|refund_amount|feedback_text|preceding_(up|down)grade` em `src/churn_diag/risk.py`
- verificação(teste): @principle:P-002

## P-003 [DEVE] Nenhum número do relatório é digitado à mão

Todo número marcado no relatório do CEO (`<!--m:chave-->valor`) é conferido
contra `outputs/metrics.json`, gerado pelo pipeline. Se a IA (ou um humano)
"arredondar para cima" ou inventar um valor, o teste falha.

- verificação(teste): @principle:P-003

## P-004 [DEVE] Correlação não é vendida como causa

Todo achado registrado carrega o tipo de afirmação que sustenta —
`descricao`, `predicao` ou `hipotese_causal` — e hipótese causal sempre vem com
o teste que a validaria. Um achado sem rótulo não entra no relatório.

- verificação(teste): @principle:P-004

## P-005 [DEVE] Processamento de dados em Polars

Stack definida: Python 3.14 + Polars. pandas não entra no código de produção
(scikit-learn recebe arrays NumPy direto do Polars).

- verificação(proibido): `^\s*(import pandas|from pandas)` em `src/**/*.py`

## P-006 [DEVE] Resultado reprodutível

Mesma entrada → mesma saída, byte a byte. Toda aleatoriedade passa por uma
semente única declarada na configuração.

- verificação(obrigatório): `^SEED: Final\[int\] = \d+` em `src/churn_diag/config.py`
- verificação(teste): @principle:P-006

## P-007 [DEVE] Segredos nunca em código

O projeto não precisa de credenciais; se um dia precisar, vêm de variável de
ambiente.

- verificação(proibido): `(sk-[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|(api[_-]?key|password|token)\s*[:=]\s*["'][^"']{8,})` em `src/**/*.py`

## P-008 [RECOMENDADO] Os dados brutos são somente-leitura

O pipeline nunca escreve no diretório dos CSVs originais; toda saída vai para
`outputs/`. Correções de qualidade (ex.: deduplicação) são feitas em memória e
registradas no relatório de qualidade.

- verificação(proibido): `write_csv\(\s*(DATA_DIR|data_dir)` em `src/**/*.py`
