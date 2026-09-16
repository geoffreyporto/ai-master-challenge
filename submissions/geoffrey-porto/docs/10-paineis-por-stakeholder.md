# Painéis por stakeholder — metodologia e leitura

> Página: [`../solution/dashboard/index.html`](../solution/dashboard/index.html)
> (abre por `file://`, sem servidor e sem internet).
> Especificação: `solution/.spec/features/paineis/`.
> Este documento explica **como** os cinco painéis foram construídos e, mais
> importante, **o que cada um se recusa a mostrar**.

---

## 1. O desenho

Cinco painéis, um por stakeholder, cada um com os quatro níveis de análise na
mesma ordem — porque a ordem é o argumento:

| Nível | Pergunta | O que aparece no painel |
|---|---|---|
| Descritivo | O que aconteceu? | Série, distribuição ou carga — o fato, sem interpretação |
| Diagnóstico | Por que aconteceu? | O corte que separa, com o teste que o sustenta (ou a admissão de que não separa) |
| Preditivo | O que vem? | Projeção com a confiabilidade declarada ao lado |
| Prescritivo | O que fazer? | Ações com grau de confiança, incluindo as ações a **não** tomar |

| Painel | Público | Pergunta que ele responde |
|---|---|---|
| **CEO** | Comitê executivo | A empresa está perdendo receita mais rápido do que ganha? |
| **Vendas** | Liderança comercial | Onde a receita nasce e onde ela vaza? |
| **Marketing** | Aquisição | Que canal traz cliente que fica? |
| **Financeiro** | FP&A | Quanto da receita recorrente está em risco, e quanto já virou perda? |
| **Operações / CS** | CS e suporte | Onde o cliente trava, e a fila do CS está na ordem certa? |

## 2. A regra que governa a página: nenhum número nasce aqui

`churn_diag.dashboards` monta o payload a partir das mesmas fontes do
relatório, e a página só desenha. Três consequências práticas:

**a) KPI carrega a origem.** Cada cartão mostra a chave de onde veio
(`metrics.json → mrr_churn_dec24_pct`), e o teste
`test_todo_kpi_com_chave_bate_com_o_pipeline` compara valor a valor contra o
pipeline recalculado. São 15+ KPIs conferidos a cada execução da suíte.

**b) A série do painel é a série do relatório.** Este foi o erro que quase
entrou: ao escrever a agregação mensal do painel, a primeira versão calculava o
churn de dezembro como 6,75% — contra 3,52% no relatório. Numerador e
denominador de coortes diferentes. A correção foi delegar a `monthly_churn`, a
função canônica, em vez de recalcular. Um painel que discorda do relatório vale
menos que nenhum painel, e o `AC-047` existe só para travar isso.

**c) O que o dataset não sustenta fica em branco, declarado.** Cada painel
termina numa seção "O que este painel NÃO mostra".

## 3. As lacunas, por painel

Esta é a parte do documento que um painel comercial normalmente esconde.

| Painel | KPI ausente | Por quê |
|---|---|---|
| CEO | Causa da quebra de set–out/2024 | Nenhuma tabela registra preço, release, campanha ou concorrente |
| CEO | NRR / expansão | `upgrade_flag` e `downgrade_flag` não têm data |
| Vendas | Pipeline, conversão, ciclo | Não existe tabela de oportunidades — só assinaturas fechadas |
| Vendas | Churn pós-upgrade datado | Mesmas flags sem data: não dá para ordenar upgrade e saída |
| Marketing | **CAC, ROI, verba de mídia** | Não há custo de aquisição nem investimento por campanha |
| Marketing | **LTV** | Sem margem e sem custo de serviço, só existe receita observada |
| Marketing | Campanha e oferta | Não há identificador de campanha nem de desconto de entrada |
| Financeiro | Margem, custo, fluxo de caixa | Só receita recorrente contratada |
| Financeiro | Descontos e cobrança efetiva | MRR contratado ≠ faturado ≠ pago |
| Operações | **Frequência de login** | Não existe tabela de sessão |
| Operações | Adoção de funcionalidade de IA | As funcionalidades são anônimas (`feature_1`…`feature_40`) |
| Operações | Health score longitudinal | Depende de série de uso confiável; 76,6% dos eventos têm data inconsistente |

O teste `test_kpi_impossivel_nao_vira_numero` varre os rótulos dos KPIs em
busca de `cac`, `ltv`, `roas`, `verba` e `login`. Se alguém adicionar um desses
cartões — com número estimado, "só para não ficar vazio" — a suíte quebra. É a
mesma lógica do portão de rastreabilidade do relatório, aplicada à tela.

## 4. O que cada painel diz de desconfortável

- **CEO:** a projeção vem de uma única variável (idade da assinatura,
  ROC 0,59 fora do tempo), e o painel diz isso no próprio bloco preditivo. A
  ação de maior valor não é uma campanha: é instituir um log de eventos de
  negócio.
- **Vendas:** nenhuma vertical se separa depois da correção de Holm. A diferença
  entre indústrias é tamanho de base, não propensão a sair. E o painel recomenda
  explicitamente **não** prometer retenção via contrato anual — o efeito causal
  medido é indistinguível de zero.
- **Marketing:** o painel de aquisição existe, mostra volume e MRR por canal, e
  conclui que o canal não prevê quem fica. A recomendação principal é
  instrumentar custo antes do próximo ciclo, porque sem custo não há CAC.
- **Financeiro:** reembolsos somam US$ 8.652 no dataset inteiro, contra
  US$ 662 mil de MRR excedente perdido no 4º tri. O painel diz que endurecer
  política de reembolso não move o resultado.
- **Operações:** tempo de resolução e primeira resposta são praticamente
  idênticos entre prioridades — a fila não está sendo priorizada. E as taxas de
  erro por funcionalidade ficam todas entre 6,0 e 6,6 por 100 usos: distribuição
  uniforme, não um gargalo identificável.

## 5. Stack e por que ela

| Camada | Escolha | Motivo |
|---|---|---|
| Estrutura | HTML5 semântico | Abre em qualquer navegador, sem build |
| Lógica | **TypeScript** compilado com `tsc` | Tipagem no contrato do payload: se o pipeline mudar o formato, a compilação acusa |
| Estilo | **Tailwind** (vendorizado) + **CSS3** próprio | Tailwind para o layout, CSS3 para o que ele não cobre (gradiente de fundo, `font-feature-settings: tnum` para números alinhados, regras de impressão) |
| Gráficos | **Chart.js 4** + **Plotly.js 2** (vendorizados) | Chart.js para barras (tooltip, legenda clicável, hover); Plotly para as duas séries (zoom, pan, hover unificado, exportação nativa). Barra sempre começa em zero; série temporal mostra o eixo inteiro |
| Dados | `data.js` como atribuição global | `fetch` em `file://` esbarra em CORS; `<script>` não |

Dependências vendorizadas em `dashboard/vendor/` (~1,6 MB), não via CDN: a página
precisa funcionar na máquina do avaliador, offline, daqui a seis meses.

## 6. Reproduzir

```bash
cd submissions/geoffrey-porto/solution
uv run python -m churn_diag        # recalcula e reescreve dashboard/data.js
tsc -p dashboard/tsconfig.json     # recompila app.js
uv run pytest tests/test_dashboards.py -q
open dashboard/index.html
```
