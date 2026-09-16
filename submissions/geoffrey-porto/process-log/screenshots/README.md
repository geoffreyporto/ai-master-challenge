# Capturas de tela

Os cinco painéis de decisão, renderizados a partir de
[`../../solution/dashboard/index.html`](../../solution/dashboard/index.html).
Cada imagem é a página inteira, do cabeçalho ao rodapé — inclusive a seção
"O que este painel NÃO mostra", que é a parte que um print de dashboard
normalmente corta.

| Arquivo | Painel | O que a captura prova |
|---|---|---|
| `01-painel-ceo.png` | CEO | A série mensal com o limite de controle, a quebra de regime anotada (1,2× → 4,1×) e os três cenários de recuperação |
| `02-painel-vendas.png` | Vendas | MRR por plano, MRR perdido por vertical e a recomendação explícita de **não** prometer retenção via contrato anual |
| `03-painel-marketing.png` | Marketing | Base e churn precoce por canal — e as três lacunas (CAC, LTV, campanha) que o dataset não sustenta |
| `04-painel-financeiro.png` | Financeiro | US$ 8.652 de reembolso contra US$ 662 mil de MRR excedente perdido: a prova de que reembolso não é o problema |
| `05-painel-operacoes.png` | Operações / CS | Tempos de resolução idênticos entre prioridades, erro uniforme entre funcionalidades e a fila do CS ordenada por risco × MRR |

## Como foram feitas

Não são fotos de tela: a página foi servida localmente, renderizada em
viewport de 1.360 px e capturada inteira via `html2canvas` a 1,6×, depois
reduzida para 1.400 px de largura. Qualquer pessoa reproduz:

```bash
cd submissions/geoffrey-porto/solution
uv run python -m churn_diag                 # regenera dashboard/data.js
python3 -m http.server 8777 --directory dashboard
```

## Evidência além das imagens

Uma imagem não é verificável — um log de terminal pode ser reproduzido com um
comando, um print não. Por isso as capturas são a **quinta** forma de
evidência desta entrega, não a única:

- **Chat export** — [`../chat-exports/conversa-claude-code.md`](../chat-exports/conversa-claude-code.md)
- **Transcrições de execução** — [`../evidencias/`](../evidencias/) (comandos e saídas reais)
- **Histórico git** — um commit por tarefa, `T-0XX <feature>: …`
- **Notebook comentado e executado** — [`../../solution/notebooks/diagnostico_churn.ipynb`](../../solution/notebooks/diagnostico_churn.ipynb)
- **Figuras do pipeline** — [`../../solution/outputs/figures/`](../../solution/outputs/figures/) (10 PNGs regeneradas a cada execução)
