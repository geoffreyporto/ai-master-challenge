# Streamlit — Diagnóstico de Churn RavenStack

Versão leve do diagnóstico para quem prefere abrir um link em vez de clonar o
repositório. Não recalcula nada: lê `../outputs/metrics.json` e os CSVs que o
pipeline já gravou — o mesmo princípio do resto da entrega (nenhum número
nasce na tela) vale aqui também.

## Rodar local

```bash
cd submissions/geoffrey-porto/solution
uv run python -m churn_diag        # garante que outputs/ existe e está atualizado
pip install -r streamlit_app/requirements.txt
streamlit run streamlit_app/app.py
```

## Deploy no Streamlit Community Cloud

1. Em [share.streamlit.io](https://share.streamlit.io), **New app**.
2. Repositório: o fork `geoffreyporto/ai-master-challenge`, branch
   `submission/geoffrey-porto`.
3. Main file path: `submissions/geoffrey-porto/solution/streamlit_app/app.py`.
4. Deploy. O Streamlit Cloud lê `requirements.txt` nesta mesma pasta.

Não depende do pacote `churn_diag` nem de Python 3.14 — só lê CSVs e JSON com
`pandas`, então roda na versão de Python padrão do Streamlit Cloud sem
configuração extra.

## O que este app NÃO substitui

- **Relatório completo:** [`../RELATORIO.md`](../RELATORIO.md) — a versão
  para o CEO, com as limitações e as perguntas em aberto por extenso.
- **Painéis por stakeholder:** [`../dashboard/`](../dashboard/) — cinco
  visões (CEO, Vendas, Marketing, Financeiro, Operações), interativas em
  Chart.js/Plotly, com as lacunas do dataset declaradas por painel.
- **Pipeline e testes:** [`../src/churn_diag/`](../src/churn_diag/) — a
  fonte de todo número que aparece aqui.
