# Spec: Publicação (Streamlit Community Cloud + Vercel)

> feature: publicacao
> status: em-implementacao

## Contexto

O avaliador precisa abrir a proposta sem instalar nada. O app completo vai
para o Streamlit Community Cloud; na Vercel ficam uma página estática com os
resultados e a API `/api/route` em Rust, com o mesmo modelo e a mesma política.
Na versão pública o rascunho do Pioneer fica desligado: a chave é do autor.

## Histórias

### US-015 — O avaliador usa a proposta por um link

Como avaliador, quero abrir o app e chamar o roteador por URL pública, para
avaliar sem configurar ambiente.

#### AC-042 — A demo pública não gera rascunho

- **Dado** o app com `SUPPORT_PUBLIC_DEMO=1`
- **Quando** a aba Roteador é aberta
- **Então** o botão de rascunho não aparece e o app explica que o rascunho está desligado na versão pública
- **E** nenhuma chamada ao Pioneer é feita

#### AC-043 — O app sobe do zero sem artefatos locais

- **Dado** um ambiente novo com os CSVs e sem `outputs/models/`
- **Quando** o app é aberto
- **Então** o app roda o pipeline uma vez antes de carregar a página e não refaz se os artefatos já existem

#### AC-044 — A API da Vercel decide igual ao modelo avaliado

- **Dado** a função `api/route` com o modelo embutido no binário
- **Quando** recebe tickets do hold-out
- **Então** a fila e a ação são as mesmas do golden do Python, e `GET /api/route/health` responde ok

#### AC-045 — A página estática mostra só números do pipeline

- **Dado** a página `public/index.html` da Vercel
- **Quando** o pipeline roda
- **Então** `public/data.json` é regenerado a partir de `outputs/metrics.json` e todo número exibido vem dele

## Fora de escopo

- Autenticação e limite de taxa da API pública (protótipo; exigência para produção em `docs/03`).
- Rascunho do Pioneer na versão pública.

## Suposições

| ID | Suposição | Status | Resolução |
|---|---|---|---|
| ASM-011 | Publicar os dois CSVs (licença CC0) no repositório é permitido | confirmada | Os dois datasets do Kaggle são CC0; a demo pública precisa deles para rodar o pipeline. |

## Perguntas em aberto

Nenhuma além de Q-004 (provedor hospedado), que motiva o rascunho desligado.
