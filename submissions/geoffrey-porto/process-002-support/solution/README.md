# Solução — Challenge 002 (Redesign de Suporte)

Comandos rodam a partir desta pasta (`solution/`).

## Pré-requisitos

- Python 3.14 + [uv](https://docs.astral.sh/uv/)
- Rust **não** é necessário para rodar: o roteador vem pré-compilado em `router/dist/`
  (macOS arm64/x86_64, Linux arm64/x86_64 estático, Windows x86_64). Só para
  recompilar ou rodar `pytest` completo: `rustup toolchain install 1.98.1 -c clippy -c rustfmt`
- Kaggle CLI (para baixar os dados) e, opcionalmente, chave do Pioneer

## Setup e pipeline

```bash
kaggle datasets download -d suraj520/customer-support-ticket-dataset -p data --unzip
kaggle datasets download -d adisongoh/it-service-ticket-classification-dataset -p data --unzip
uv sync
uv run python -m support_redesign        # ~1 min; usa o cache em outputs/pioneer/
```

Para chamar o Pioneer de novo (caches ausentes), aponte para a chave **fora do repositório**:

```bash
PIONEER_ENV_FILE=/caminho/fora/do/repo/.env uv run python -m support_redesign --pioneer
```

## Rodar o protótipo

App Streamlit (http://localhost:8501):

```bash
uv run streamlit run app/streamlit_app.py
```

O app **inicia sozinho** o roteador Rust pré-compilado da sua plataforma
(http://127.0.0.1:8080) e mostra o status no topo da página.

Para rodar só o roteador (`POST /route`, `GET /health`), sem Rust instalado:

```bash
uv run python -m support_redesign.router_bin
```

Ou chame o binário direto — ele acha o modelo `router_model.json.gz` sozinho:

```bash
./router/dist/macos-arm64/support-router        # troque pela sua plataforma
```

```powershell
router\dist\windows-x86_64\support-router.exe
```

Opções: `--addr HOST:PORTA` e `--model CAMINHO`. No macOS, se o Gatekeeper
bloquear o binário, rode `xattr -d com.apple.quarantine router/dist/macos-*/support-router`.
Para recompilar a partir do código: `cargo +1.98.1 run --release --manifest-path router/Cargo.toml`;
para regenerar todos os binários (Docker necessário): `router/build-dist.sh`.

Com o roteador no ar, a aba *Roteador* do app mostra se a decisão do Rust é a mesma do Python.
O botão *Gerar rascunho* só funciona com `PIONEER_ENV_FILE` ou `PIONEER_API_KEY` definidos
no terminal do app.

Teste rápido do roteador:

```bash
curl -s -X POST http://127.0.0.1:8080/route -H 'Content-Type: application/json' -d '{"text":"laptop screen broken, dock not detected","priority":"High"}'
```

## Provas

```bash
uv run pytest -q                                   # inclui cargo test e clippy
for f in $(ls .spec/features); do onp-spec verify $f; done
onp-spec audit --ci                                # só as perguntas de negócio abertas (Q-001…Q-004)
```

Variáveis opcionais: `SUPPORT_DATA_DIR` (CSVs em outro lugar), `ROUTER_MODEL` / `ROUTER_ADDR`
(roteador), `ROUTER_URL` (app).

## Publicação

- **Vercel** (`router/`): `npx vercel@latest deploy --prod` a partir de `router/`.
  A função `api/route.rs` usa o runtime Rust oficial com o modelo embutido;
  `public/` é servido como página estática (`data.json` é gerado pelo pipeline).
- **Streamlit Community Cloud**: arquivo principal
  `submissions/geoffrey-porto/process-002-support/solution/app/streamlit_app.py`,
  Python 3.14, dependências em `app/requirements.txt` e o secret
  `SUPPORT_PUBLIC_DEMO = "1"` (desliga o rascunho). No primeiro acesso o app só
  monta o índice de similares; o modelo servido é `router/dist/router_model.json.gz`.
