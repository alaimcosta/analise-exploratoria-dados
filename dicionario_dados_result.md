# Dicionário de dados - Matriz de Dados do Crédito Rural

Arquivos: `MATRIZ_CR_PRODUTO_MUNICIPIO_2023.csv` a `MATRIZ_CR_PRODUTO_MUNICIPIO_2026.csv`.

Volume: 1.635.490 linhas, 24 colunas de dados. Formato: CSV com `;` e números com vírgula decimal.
Período: 8 semestres, de `2023-06-01` a `2026-12-01` (o 2º semestre de 2026 é parcial).


## 1. Dimensões

| Coluna | Tipo sugerido | Descrição | Observações |
|---|---|---|---|
| `ANO_SEMESTRE_EMISSAO` | DATE | Semestre de emissão (contratação) das operações, representado por uma data: `AAAA-06-01` e `AAAA-12-01`. | 8 valores. Convenção (a confirmar): `06-01` = 1º semestre (jan–jun), `12-01` = 2º semestre (jul–dez). |
| `PRODUTO` | VARCHAR | Produto ou objeto financiado (cultura, criação ou item de investimento). | 357 valores; texto em caixa alta com acentos. Ex.: `MILHO`, `BOVINOS`, `MÁQUINAS E IMPLEMENTOS`. |
| `ATIVIDADE` | VARCHAR | Atividade econômica: `AGRÍCOLA` ou `PECUÁRIA`. | 2 valores. |
| `MODALIDADE` | VARCHAR | Modalidade/classificação do financiamento dentro da atividade. | 44 valores; alguns trazem o item do MCR (`AGROINDÚSTRIA FAMILIAR (MCR 10-11)`). Ex.: `LAVOURA`, `BOVINOCULTURA`. |
| `REGIAO` | VARCHAR | Grande região do Brasil. | 5 valores: `NORTE`, `NORDESTE`, `SUDESTE`, `SUL`, `CENTRO-OESTE`. |
| `UF` | VARCHAR | Unidade da Federação, por extenso. | 27 valores. Mapear para sigla. |
| `COD_MUNICIPIO_IBGE` | INTEGER (nulo permitido) | Código IBGE do município (7 dígitos). | 75,38% nulo. Vem com espaços à esquerda; aplicar `strip` antes do cast. |
| `MUNICIPIO` | VARCHAR (nulo permitido) | Nome do município. | 75,38% nulo; não é chave (homônimos). |
| `PROGRAMA` | VARCHAR | Programa de crédito rural, com sigla e nome. | 14 valores. Ex.: `PRONAF - PROGRAMA NACIONAL DE FORTALECIMENTO DA AGRICULTURA FAMILIAR`, `PRONAMP`, `RENOVAGRO`, `MODERFROTA`, `PCA`, `FINANCIAMENTO SEM VÍNCULO A PROGRAMA ESPECÍFICO`. |
| `SUBPROGRAMA` | VARCHAR | Subprograma, geralmente com referência ao MCR. | 56 valores. Inclui `SEM SUBPROGRAMA`. Extrair o código `MCR x-y` em coluna própria. |
| `FONTE_RECURSO` | VARCHAR | Fonte dos recursos e sua classificação (direcionada/livre, controlada/não controlada, equalizada). | 22 valores. Atributo composto: separar fonte e classificação. Ex.: `LETRA DE CRÉDITO DO AGRONEGÓCIO (LCA) - DIRECIONADA/NÃO CONTROLADA`. |

## 2. Medidas

Unidades presumidas (a confirmar): valores em R$ e área em hectares. Todas as medidas de valor e área usam vírgula decimal no CSV.

| Coluna | Tipo sugerido | Descrição | Observações |
|---|---|---|---|
| `CUSTEIO_AREA` | DECIMAL(18,2) | Área financiada em contratos de custeio. | 0 a 400.389,65. |
| `CUSTEIO_QTDE` | BIGINT | Número de contratos de custeio. | 0 a 895. |
| `CUSTEIO_VALOR` | DECIMAL(18,2) | Valor contratado em custeio. | Máx. R$ 1,16 bi em uma linha. |
| `INVESTIMENTO_AREA` | DECIMAL(18,2) | Área financiada em contratos de investimento. | 0 a 3.049.397,23. |
| `INVESTIMENTO_QTDE` | BIGINT | Número de contratos de investimento. | 0 a 1.618. |
| `INVESTIMENTO_VALOR` | DECIMAL(18,2) | Valor contratado em investimento. | Máx. R$ 2,6 bi em uma linha. |
| `COMERCIALIZACAO_QTDE` | BIGINT | Número de contratos de comercialização. | 0 a 1.032. Não há coluna de área. |
| `COMERCIALIZACAO_VALOR` | DECIMAL(18,2) | Valor contratado em comercialização. | Máx. R$ 3 bi em uma linha. |
| `INDUSTRIALIZACAO_QTDE` | BIGINT | Número de contratos de industrialização. | 0 a 17. Não há coluna de área. |
| `INDUSTRIALIZACAO_VALOR` | DECIMAL(18,2) | Valor contratado em industrialização. | Máx. R$ 2 bi em uma linha. |
| `TOTAL_AREA` | DECIMAL(18,2) | Área total da linha. | Hipótese: custeio + investimento. |
| `TOTAL_QTDE` | BIGINT | Número total de contratos da linha. | Mínimo 1: toda linha tem ao menos um contrato. Hipótese: soma das quatro finalidades. |
| `TOTAL_VALOR` | DECIMAL(18,2) | Valor total da linha. | Mínimo R$ 0,01. Hipótese: soma das quatro finalidades. |

## 3. Colunas derivadas propostas

| Coluna | Como obter |
|---|---|
| `semestre_ini` / `semestre_fim` | Do `ANO_SEMESTRE_EMISSAO`: `06-01` → jan–jun; `12-01` → jul–dez. |
| `ano_safra` | Semestre jan–jun do ano Y → `Safra (Y-1)/Y`; semestre jul–dez do ano Y → `Safra Y/(Y+1)` (rótulo "Safra AA/AA"). |
| `ano_civil` | Ano do semestre. |
| `uf_sigla` | Mapeamento do nome da UF para a sigla. |
| `fonte_recurso_nome` / `fonte_recurso_classe` | Separação de `FONTE_RECURSO` no último ` - `. |
| `programa_sigla` | Texto antes do primeiro ` - ` de `PROGRAMA`. |
| `subprograma_mcr` | Regex `MCR [0-9-]+` em `SUBPROGRAMA`. |