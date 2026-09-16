# Referência do candidato — *Features Engineering*

Cópia versionada dos artefatos que o candidato trouxe como referência de
engenharia de features (originais em `features/`, na raiz do fork):

| Arquivo | O que é |
|---|---|
| `Features Engineering.md` | Proposta de 20 features + 8 controles + 3 derivadas + exclusões por vazamento |
| `screen_ravenstack_features.py` | Script de triagem (pandas/sklearn): painel conta × snapshot mensal, janelas de 90 dias, rótulo = evento de churn não-reativação nos 30 dias seguintes |
| `ravenstack_feature_screen.json` | Saída da triagem: ROC-AUC 0,604 · AP 0,144 no teste (set–out/2024) e importância por permutação |

Ficam **dentro da pasta da submissão** porque a regra do desafio é explícita:
"só modifique arquivos dentro de `submissions/seu-nome/` — PRs que alteram
outros arquivos serão rejeitados" (CONTRIBUTING.md). A pasta `features/` na
raiz continua no disco, fora do controle de versão deste PR.

**Replicação:** o desenho desta triagem foi reproduzido em Polars
(`solution/src/churn_diag/account_panel.py`) e bate linha a linha: 3.392 de
treino e 854 de teste, com as mesmas taxas de evento (6,93% e 10,66%), e
precisão média 0,145 contra 0,144 publicados. O ROC fica em 0,57 contra 0,604
porque a replicação roda sem as três flags sem data (quarentena P-009) e sem
tendência/recência de uso (linha do tempo quebrada).

Comparação feature a feature: [`../04-matriz-de-features.md`](../04-matriz-de-features.md).
Replicação do desenho e medição das features de taxa: feature `validacao-features`
em [`../../solution/.spec/features/validacao-features/`](../../solution/.spec/features/validacao-features/).
