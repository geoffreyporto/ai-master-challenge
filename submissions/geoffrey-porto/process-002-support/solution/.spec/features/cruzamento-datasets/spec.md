# Spec: Cruzamento dos datasets (mudança de domínio)

> feature: cruzamento-datasets
> status: em-implementacao

## Contexto

O critério do challenge pede o cruzamento dos dois datasets. O cruzamento útil
é aplicar o classificador treinado no Dataset 2 (TI corporativa) aos tickets do
Dataset 1 (eletrônicos de consumo) e verificar se o roteador sabe quando não
sabe.

## Histórias

### US-007 — O Diretor vê o que acontece quando chega ticket de um domínio que o modelo não conhece

Como Diretor de Operações, quero saber como o roteador se comporta com tickets
diferentes dos de treino, para confiar que ele manda o desconhecido para humano.

#### AC-021 — Todos os tickets do Dataset 1 são pontuados

- **Dado** as 8.469 descrições do Dataset 1 sem os `{placeholders}` e com a normalização do treino
- **Quando** o classificador pontua todas
- **Então** cada ticket recebe fila prevista, confiança e ação da política, e a distribuição por fila é reportada

#### AC-022 — A mudança de domínio é testada e muda a ação

- **Dado** as confianças no Dataset 1 e no teste do Dataset 2
- **Quando** as distribuições são comparadas
- **Então** o teste de Kolmogorov-Smirnov é reportado
- **E** a fração enviada a humano no Dataset 1 é maior que no teste do Dataset 2

## Fora de escopo

- Retreinar para o domínio do Dataset 1 (os rótulos de tipo são aleatórios).

## Suposições

Nenhuma.

## Perguntas em aberto

Nenhuma.
