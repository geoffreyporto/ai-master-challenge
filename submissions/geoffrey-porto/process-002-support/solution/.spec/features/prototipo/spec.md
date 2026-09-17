# Spec: Protótipo funcional (app + roteador)

> feature: prototipo
> status: em-implementacao

## Contexto

"Não quero só um PowerPoint. Quero ver algo rodando." O protótipo tem duas
partes: um app Streamlit para o Diretor e os agentes, e um roteador HTTP em
Rust (axum) que aplica o mesmo modelo e a mesma política em produção.

## Histórias

### US-009 — O Diretor abre um app e vê diagnóstico, roteamento e ROI com dado real

Como Diretor de Operações, quero um app com filtros e um roteador ao vivo,
para ver a proposta funcionando sem depender de slides.

#### AC-025 — O app abre todas as seções com dado real

- **Dado** o pipeline executado
- **Quando** o app é aberto
- **Então** as seções Diagnóstico, Roteador, Fronteira, Similares e ROI renderizam sem erro

#### AC-026 — A demonstração usa ticket sorteado do hold-out, não exemplo escolhido

- **Dado** a seção Roteador
- **Quando** o usuário pede um ticket
- **Então** o app sorteia um ticket do teste e mostra fila verdadeira, fila prevista, confiança, ação e motivo
- **E** as métricas exibidas são as do hold-out inteiro

### US-010 — A operação chama um roteador HTTP que decide igual ao modelo avaliado

Como engenharia da operação, quero um endpoint `/route` rápido e sem
dependência de nuvem, que decida exatamente como o modelo medido.

#### AC-027 — O roteador responde fila, confiança e ação

- **Dado** o roteador rodando com o modelo exportado
- **Quando** recebe `POST /route` com um texto
- **Então** responde fila, confiança, margem, ação e motivo
- **E** `GET /health` responde ok

#### AC-028 — O roteador Rust decide igual ao Python no hold-out inteiro

- **Dado** todos os tickets do teste
- **Quando** Python e Rust pontuam os mesmos textos
- **Então** a fila prevista e a ação são idênticas em 100% dos tickets e as probabilidades diferem menos que 1e-9

#### AC-029 — O roteador recusa entrada inválida sem cair

- **Dado** o roteador rodando
- **Quando** recebe texto vazio, texto acima do limite ou JSON inválido
- **Então** responde erro 4xx com mensagem e continua respondendo

### US-013 — O avaliador sobe o roteador sem instalar Rust

Como avaliador do challenge, quero rodar o roteador com um comando, sem
`cargo` nem toolchain Rust, para testar a proposta com autonomia.

#### AC-038 — Binários prontos rodam o roteador sem compilar

- **Dado** a pasta `router/dist/` com binários para macOS (arm64, x86_64), Linux (arm64, x86_64) e Windows (x86_64), o modelo compactado e o arquivo de checksums
- **Quando** o lançador Python escolhe o binário da plataforma e o inicia
- **Então** `GET /health` responde ok e as decisões em tickets do hold-out são iguais às do Python
- **E** todo binário e o modelo conferem com `SHA256SUMS`, e o modelo compactado é o mesmo exportado pelo pipeline

#### AC-039 — O app sobe o roteador sozinho

- **Dado** o roteador fora do ar e um binário para a plataforma
- **Quando** o app é aberto
- **Então** o app inicia o binário e a aba Roteador mostra a decisão do Rust ao lado da do Python
- **E** sem binário para a plataforma, o app continua funcionando e mostra como compilar

### US-014 — O avaliador vê o fluxo funcionando num navegador real

Como avaliador, quero testes funcionais ponta a ponta no navegador, com
capturas de tela, para confiar que o app funciona fora dos testes unitários.

#### AC-040 — O fluxo do Diretor funciona no navegador (Playwright)

- **Dado** o app Streamlit rodando com o roteador pré-compilado
- **Quando** o Playwright abre o app no Chrome e percorre as abas
- **Então** os KPIs aparecem, o filtro de canal muda a contagem, o ticket sorteado mostra fila, ação e a mesma decisão do Rust, a prioridade Critical nunca sai automática, a busca de similares traz resultados e mudar uma premissa muda o ROI
- **E** cada etapa gera uma captura de tela em `process-log/screenshots/`

#### AC-041 — O rascunho funciona no navegador ou avisa a falta de chave

- **Dado** a aba Roteador com um ticket sorteado
- **Quando** o usuário clica em Gerar rascunho
- **Então** com chave do Pioneer aparecem o texto mascarado, o rascunho que requer aprovação e o veredito do guardrail
- **E** sem chave aparece o aviso de como configurá-la, sem erro

## Fora de escopo

- React/Node, microserviços, Docker, K8s (sem valor para os critérios). O Docker é usado só na máquina do autor para compilar os binários de Linux e Windows.
- Assinatura de código dos binários (macOS pode pedir liberação no Gatekeeper).
- Dashboard "tempo real" com streaming falso.
- Autenticação do roteador (protótipo local; exigência para produção listada em `docs/03`).

## Suposições

| ID | Suposição | Status | Resolução |
|---|---|---|---|
| ASM-008 | Streamlit local (ou Community Cloud) basta como "algo rodando" para o Diretor | confirmada | Pedido explícito do dono do projeto: Streamlit app + deploy. |

## Perguntas em aberto

Nenhuma.
