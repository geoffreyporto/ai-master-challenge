# Guia de implementação e análise — Challenge 002

Derivado de `Guide of impementation and Analytic - IT Support.md`, com três
mudanças: (1) toda afirmação dos docs de referência foi **re-medida** antes de
entrar aqui; (2) o escopo foi cortado ao que cabe em < 4 h sem perder os
critérios do challenge; (3) cada passo aponta o critério de aceite (AC) que o
prova.

## 1. O que foi re-medido e o que mudou

| Afirmação nos docs | Medido | Consequência |
|---|---|---|
| README: `Ticket Type` com 3 valores | **5** (Technical issue, Billing inquiry, Product inquiry, Refund request, Cancellation request) | Segmentos = 4 × 4 × 5 = 80 |
| README: ~30.000 tickets | 8.469 linhas | Volume do ROI vem do README, não do arquivo |
| "156 placeholders distintos" | Depende do regex (169 com `\{[a-z_ ]+\}`) | Regex fica declarado em código |
| 49,3% dos fechados resolvidos antes da 1ª resposta | 49,3% | Confirmado |
| Kruskal-Wallis p = 0,28–0,92 | 0,28–0,92 | Confirmado |
| B0 TF-IDF+LR acc 0,866 / macro-F1 0,868 | 0,866 / 0,868 (split 80/20) | Confirmado; no split 70/10/20 o número é recalculado |
| Schema Pioneer com `multi_label:false, top_k:3` | Resposta **vazia**; `top_k` e `multi_label:true` também | Só top-1 + confiança; sem margem top1−top2 |
| GLiFormer "talvez" no Pioneer | Ausente do catálogo | Fora do benchmark |
| Upload de dataset por API | Só pelo dashboard | LoRA (B4) vira passo opcional do usuário |
| "Zero-shot pode ficar abaixo do TF-IDF" | GLiNER2 multi-large (+ fallback large): macro-F1 0,288 no hold-out inteiro; DeepSeek-V4-Flash: 0,392 em 400 tickets (B0: 0,867 / 0,888) | Confirmado com folga; hospedados fora do roteamento |
| Guarda de domínio não previsto nos docs | Sem ele, 18,4% dos tickets do Dataset 1 seriam roteados para filas de TI | Guarda por fração de n-gramas conhecidos (P-005 inclui o Rust) |

## 2. Execução por fase (CRISP-DM → feature → AC)

### Fase 2–3: entendimento e preparação

1. `io.load_d1/load_d2`: leitura em Polars; `data/` é somente-leitura (P-010).
2. `text.normalize`: minúsculas, remove `{placeholders}`, tudo que não é letra
   vira espaço, colapsa espaços. **A mesma função** serve treino, app e — por
   reimplementação testada — o roteador Rust (P-005).
3. `audit`: placeholders, χ² de uniformidade, χ² Subject × Type, intervalos
   negativos, unicidade de resoluções, domínios de e-mail (AC-001…AC-003).

### Fase 4: modelagem

| Linha | Modelo | Papel |
|---|---|---|
| B0 | TF-IDF (uni+bigramas, sublinear) + regressão logística balanceada | Baseline e candidato a produção (exportável para Rust) |
| B1 | Model2Vec `potion-base-8M` + regressão logística | Rápido, offline; também alimenta o índice de similares |
| B2 | `fastino/gliner2-multi-large-v1` → fallback `fastino/gliner2-large-v1`, zero-shot (Pioneer, `store:false`) | Valor sem treino; candidato a segunda opinião (AC-030, AC-032) |
| B3 | `deepseek-ai/DeepSeek-V4-Flash` como classificador, amostra estratificada de 400 | Custo/latência de LLM contra modelo pequeno (AC-031) |
| B4 (opcional) | GLiNER2 LoRA (Pioneer) | Teto do tier pesado, se houver tempo |

- Split estratificado 70/10/20, semente única (AC-009).
- Escolha do modelo de produção por macro-F1 **na validação** (AC-011).
- ECE com 15 faixas no teste (AC-012).

### Fase 4b: decisão (a fronteira)

1. **Limiar por fila**: para cada fila prevista, menor limiar de confiança com
   precisão ≥ meta na validação; sem limiar viável → só-humano (AC-013).
2. **Conformal split** (LAC): `q̂` = quantil (1−α) de `1 − p(verdadeira)` na
   validação; conjunto = filas com `p ≥ 1 − q̂`. Conjunto com mais de uma fila
   → humano (AC-015, AC-016).
3. **Regras fixas**: `Miscellaneous` → humano; `Critical` → confirmar.
4. **Rotear ≠ resolver**: conceder acesso/direitos, reembolso, cancelamento e
   resposta ao cliente ficam com humano em qualquer confiança.

### Fase 5: avaliação

- Cobertura, precisão dos automáticos e fila humana no teste (AC-014).
- Recall@1/5/10 do índice de similares contra acerto por sorteio (AC-019).
- Dataset 1 inteiro pelo roteador; KS das confianças D1 × D2 (AC-021, AC-022).
- ROI líquido: triagem poupada − retrabalho criado pelos erros (AC-024).

### Fase 6: implantação

- `python -m support_redesign` gera `outputs/metrics.json`, o modelo exportado
  e o golden do hold-out.
- `router/` (axum 0.8, tokio): `POST /route`, `GET /health`; paridade com o
  Python no hold-out inteiro (AC-028).
- `app/streamlit_app.py`: Diagnóstico, Roteador (ticket sorteado + rascunho
  com máscara e guardrail), Fronteira, Similares, ROI (AC-025, AC-026, AC-036).
- Privacidade: `gliner2-privacy-filter-PII-multi` antes do LLM,
  `gliguard-PII-multi` depois (AC-033…AC-035).

## 3. Comandos

```bash
cd submissions/geoffrey-porto/process-002-support/solution
uv sync
uv run python -m support_redesign            # pipeline completo
uv run pytest                                 # inclui cargo test do roteador
uv run streamlit run app/streamlit_app.py     # app
uv run python -m support_redesign.router_bin    # roteador pré-compilado em :8080 (sem Rust)
router/build-dist.sh                          # autor: recompila os 5 binários (Docker)
onp-spec verify <feature> && onp-spec audit --ci
```

Pioneer (opcional): `export PIONEER_API_KEY=...` ou `PIONEER_ENV_FILE=/caminho/fora/do/repo/.env`
antes de `uv run python -m support_redesign --pioneer`.

## 4. O que ficou fora (e por quê)

| Item | Motivo |
|---|---|
| Erlang C / SimPy | O cenário de ROI responde "quanto economiza" com menos premissas |
| cleanlab, MAPIE | Conformal em ~15 linhas sem dependência; ruído de rótulo vira suposição (ASM-003) |
| Triagem de prioridade por modelo | Prioridade do Dataset 1 é aleatória — não há sinal |
| Avaliar a qualidade técnica dos rascunhos do LLM | Nenhuma resolução real para comparar; medimos só vazamento de PII e guardrail (AC-037) |
| React, Docker, K8s, streaming falso | Zero valor para os critérios |
