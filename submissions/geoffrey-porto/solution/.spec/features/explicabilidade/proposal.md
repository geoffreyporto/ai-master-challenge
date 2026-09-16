# Proposal: explicabilidade

## Why

O documento *Model interpretability: explainability plots* pede cinco gráficos
(beeswarm, dependência, waterfall, heatmap por ambiente e escada de CATE). Duas
restrições reais mudam como isso é feito aqui:

1. **A biblioteca `shap` não instala em Python 3.14** — ela depende de `numba`,
   que só suporta até 3.9. Em vez de trocar a stack, os valores de Shapley são
   calculados **exatos, por enumeração de coalizões** (2^k), com função de valor
   intervencional. Sem dependência nova e sem aproximação.
2. **O modelo com as 5 tabelas empata com o acaso fora do tempo** (0,53). Então
   a explicabilidade entra como **auditoria**, não como narrativa: os gráficos
   servem para mostrar que não há estrutura estável, e não para contar uma
   história bonita sobre features que não preveem nada.

## What Changes

- Valores de Shapley exatos para 8 variáveis de negócio do painel fora do tempo.
- Os cinco gráficos, com a leitura de auditoria escrita junto de cada um.
- Um sexto, específico desta entrega: o **waterfall exato do score de produção**
  (perda esperada = risco por idade × MRR, por assinatura) — o único que o CS
  usa de verdade, e que não precisa de aproximação nenhuma.
- Seção no relatório do CEO explicando o que a explicação revela.

## Impact

- Fecha a pergunta "o modelo funciona?" com gráfico, não só com métrica.
- Não muda o score nem as recomendações.
- **Fora de escopo:** usar SHAP para justificar ação — explicar um modelo sem
  sinal não vira evidência causal (isso é o papel do DML e do experimento).
