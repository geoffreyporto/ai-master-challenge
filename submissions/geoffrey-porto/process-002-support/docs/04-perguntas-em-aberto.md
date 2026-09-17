# Perguntas em aberto (negócio)

Mantidas **abertas** de propósito: só o dono da operação responde. Cada uma
registra a decisão de projeto tomada na ausência da resposta.

## Q-001 — Existe export real do help desk?

| Campo | Conteúdo |
|---|---|
| Estado | aberta |
| Tipo | dado |
| Por que importa | Sem tempos reais não há gargalo, driver de CSAT nem desperdício medido |
| O que os dados mostram | Dataset 1 sintético: placeholders em 100% das descrições, categorias uniformes (χ² p ≥ 0,11), 49% dos fechados "resolvidos antes da 1ª resposta" |
| O que não permitem | Qualquer afirmação sobre onde o fluxo trava |
| Fonte da resposta | Diretor de Operações / admin do help desk |
| Impacto se não respondida | Diagnóstico fica como pipeline pronto + resultado nulo |
| Decisão na ausência | Rodar os testes mesmo assim, com poder estatístico, e declarar a lacuna |
| O que bloqueia | Achados reais de gargalo (US-002, US-003) |
| Dono | Diretor de Operações |
| Prazo | Antes do piloto |

## Q-002 — Quanto custa um roteamento errado e qual precisão é aceitável?

| Campo | Conteúdo |
|---|---|
| Estado | aberta |
| Tipo | regra de negócio |
| Por que importa | Define o limiar por fila e, portanto, a cobertura automática |
| O que os dados mostram | Curva risco × cobertura por fila no hold-out |
| O que não permitem | O custo de cada erro (retrabalho, SLA, risco) |
| Fonte da resposta | Coordenação de suporte + segurança (filas Access / Administrative rights) |
| Impacto se não respondida | Meta pode estar alta (cobertura menor) ou baixa (retrabalho maior) |
| Decisão na ausência | Precisão-alvo 95% (ASM-004); `Miscellaneous` só humano (ASM-005) |
| O que bloqueia | Ajuste fino da política para produção |
| Dono | Coordenação de suporte |
| Prazo | Antes do piloto |

## Q-003 — Volume mensal, minutos de triagem e custo/hora reais?

| Campo | Conteúdo |
|---|---|
| Estado | aberta |
| Tipo | parâmetro de ROI |
| Por que importa | O ROI em R$ é linear nesses três números |
| O que os dados mostram | README: ~30.000 tickets/ano; o arquivo tem 8.469 linhas |
| O que não permitem | Minutos de triagem e custo/hora |
| Fonte da resposta | Financeiro + WFM do suporte |
| Impacto se não respondida | ROI fica como cenário, não como compromisso |
| Decisão na ausência | 2.500 tickets/mês, 3 min triagem, 15 min retrabalho, R$ 60/h (ASM-007), com faixas baixa/base/alta |
| O que bloqueia | Business case final |
| Dono | Diretor de Operações |
| Prazo | Antes da aprovação do piloto |

## Q-004 — Texto de ticket pode ir para provedor hospedado?

| Campo | Conteúdo |
|---|---|
| Estado | aberta |
| Tipo | governança de dados / jurídico |
| Por que importa | Classificação GLiNER2, máscara de PII, guardrail e rascunho (DeepSeek) rodam no Pioneer |
| O que os dados mostram | A máscara acha nome e e-mail inseridos com recall medido (AC-033); rascunhos da amostra não vazaram PII (AC-037) |
| O que não permitem | Garantia contratual de retenção, região e uso do dado pelo provedor |
| Fonte da resposta | Jurídico / DPO + contrato com o Pioneer |
| Impacto se não respondida | Tier hospedado não entra em produção; o roteador local (Rust) segue funcionando sozinho |
| Decisão na ausência | Só texto mascarado sai da máquina, sempre com `store:false`; benchmarks só com o Dataset 2 público e PII Faker |
| O que bloqueia | Rascunho assistido e segunda opinião em produção |
| Dono | DPO |
| Prazo | Antes do piloto |
