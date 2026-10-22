# Dicionário de dados e plano de integração após análise

Base: Matriz de Dados do Crédito Rural (MDCR/BCB), item 2 – Quantidade e Valor dos Contratos por Produto, Região, UF, Município, Programa e Fonte de Recursos (semestre). Período: 2023–2026. Status: dicionário completo; análise concluída do schema do `warehouse.duckdb`: resultados e recomendação revisada na seção 6.

## 1. Resumo

- Foram lidos 4 arquivos (`MATRIZ_CR_PRODUTO_MUNICIPIO_2023..2026.csv`), com 1.635.490 linhas e 24 colunas de dados.
- A base é **agregada** (contagem, área e valor por combinação de dimensões) e **semestral**, e está em formato **largo**: quatro finalidades (custeio, investimento, comercialização, industrialização) × (área, quantidade, valor).
- Os números usam vírgula decimal (`21960,00`); o código IBGE vem com espaços à esquerda.
- O município está vazio em 75,38% das linhas (1.232.778). Isso limita qualquer análise municipal.
- Os 8 semestres cobrem de 2023-06-01 a 2026-12-01. O último semestre (2º de 2026) é parcial, pois estamos em outubro/2026.
- Os semestres civis coincidem com as fronteiras da safra (1º/jul a 30/jun). O 1º semestre do ano Y pertence à Safra (Y−1)/Y e o 2º semestre à Safra Y/(Y+1). Isso permite usar Ano Safra no MDCR sem perda de precisão (seção 5.2).

* **Conferência com o warehouse (21/10/2026):** os valores do MDCR coincidem com os do `credito` (mesma fonte SICOR, mesma base de data de emissão). O MDCR não traz valores novos; o ganho está em área financiada, atividade, modalidade e subprograma, e na validação dos totais. Detalhes e recomendação revisada na seção 6.

## 2. Fonte e escopo

| Item | Valor |
| --- | --- |
| Origem | BCB – MDCR (sistema SICOR) |
| Arquivos | `MATRIZ_CR_PRODUTO_MUNICIPIO_2023.csv` a `_2026.csv` |
| Linhas / colunas | 1.635.490 / 24 (+ `_arquivo` criada no perfilamento) |
| Formato | CSV com `;`, números com vírgula decimal |
| Períodos distintos | 8 (`2023-06-01`, `2023-12-01`, …, `2026-12-01`) |

## 3. Achados da análise exploratória

1. **Município majoritariamente nulo.** `COD_MUNICIPIO_IBGE` e `MUNICIPIO` têm 75,38% de nulos. A causa não está documentada nos arquivos (pode ser dado não informado, sigilo ou linhas já agregadas por UF). Medir o peso em valor (seção 7, teste 3) antes de decidir se há aba municipal.
2. **Nome de município não é chave.** Há 4.998 nomes distintos para 5.248 códigos distintos (alguns códigos podem ser variações de formatação, pois vêm com espaços). Homônimos em UFs diferentes existem. Usar o código IBGE (7 dígitos), nunca o nome.
3. **Formato largo.** As colunas de finalidade precisam de unpivot para casar com o filtro `finalidade` da dashboard.
4. **Sem área em comercialização e industrialização.** Só custeio e investimento têm colunas de área (por isso `TOTAL_AREA` provavelmente é custeio + investimento; a verificar).
5. **Atributos compostos em texto.** `FONTE_RECURSO` mistura a fonte e a classificação (`DIRECIONADA/CONTROLADA`, `LIVRE/NÃO CONTROLADA`, `EQUALIZADA`). `SUBPROGRAMA` traz o item do MCR entre parênteses (`(MCR 10-4)`). `PROGRAMA` começa com a sigla (`PRONAF - …`).
6. **`PRODUTO` é heterogêneo (357 valores).** Mistura culturas e criações (`MILHO`, `BOVINOS`) com itens de investimento (`MÁQUINAS E IMPLEMENTOS`, `RESIDÊNCIAS RURAIS`). Deve ser lido junto com `ATIVIDADE` e `MODALIDADE`.
7. **UF por extenso.** `UF` vem como `RIO GRANDE DO SUL`, não como sigla. Será preciso um mapeamento se o warehouse usar sigla.
8. **Valores extremos.** O máximo de `TOTAL_VALOR` em uma linha é R$ 3 bilhões (comercialização). É plausível em dado agregado, mas vale listar as maiores linhas e conferir.
9. **Completude de safra.** Com 1º sem/2023 a 2º sem/2026: Safra 22/23 só tem jan–jun/2023 (incompleta), as safras 23/24, 24/25 e 25/26 estão completas e a 26/27 tem só jul–dez/2026, ainda em curso.

## 4. Dicionário de dados

Tipos sugeridos para DuckDB. Descrições marcadas "(a confirmar)" são hipóteses a validar com a documentação da MDCR ou com os testes da seção 7.

### 4.1 Dimensões

| Coluna | Tipo sugerido | Descrição | Observações |
| --- | --- | --- | --- |
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

### 4.2 Medidas

Unidades presumidas: valores em R$ e área em hectares. Todas as medidas de valor e área usam vírgula decimal no CSV.

| Coluna | Tipo sugerido | Descrição | Observações |
| --- | --- | --- | --- |
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

### 4.3 Colunas derivadas propostas

| Coluna | Como obter |
| --- | --- |
| `semestre_ini` / `semestre_fim` | Do `ANO_SEMESTRE_EMISSAO`: `06-01` → jan–jun; `12-01` → jul–dez (após confirmar a convenção). |
| `ano_safra` | Semestre jan–jun do ano Y → `Safra (Y-1)/Y`; semestre jul–dez do ano Y → `Safra Y/(Y+1)` (rótulo "Safra AA/AA"). |
| `ano_civil` | Ano do semestre. |
| `uf_sigla` | Mapeamento do nome da UF para a sigla. |
| `fonte_recurso_nome` / `fonte_recurso_classe` | Separação de `FONTE_RECURSO` no último `-`. |
| `programa_sigla` | Texto antes do primeiro `-` de `PROGRAMA`. |
| `subprograma_mcr` | Regex `MCR [0-9-]+` em `SUBPROGRAMA`. |

## 5. Plano de integração à dashboard

O que se sabe do projeto: a dashboard Streamlit lê o `warehouse.duckdb`, com a tabela `credito` (microdados mensais por `competencia`) e tabelas `mart_*` pré-agregadas por `ano`/`finalidade`/`k`. As queries ficam em `data.py`, `app.py` é a casca com filtros e abas, e cada aba está em `abas/*.py::render(anos_sel, finalidade)`. Há ainda a migração em curso para Ano Safra como granularidade padrão, com env var para alternar com ano civil.

### 5.1 Natureza da integração

O MDCR é agregado e semestral; o `credito` é microdado mensal. **Não há junção linha a linha.** Dois usos possíveis, que podem coexistir:

1. **Nova fonte analítica** (produto/município/programa/fonte), alimentando abas novas ou existentes.
2. **Camada de conferência**: comparar totais do `credito` agregados por semestre/UF/finalidade com os totais do MDCR e expor divergências.

**Atualização (seção 6):** a conferência já feita mostra que os valores do MDCR batem com os do `credito`. O uso 2 (conferência) é viável e barato; o uso 1 deve se limitar ao que o `credito` não tem (área, atividade, modalidade, subprograma).

### 5.2 Eixo temporal: Ano Safra

Cada semestre do MDCR cabe inteiro em uma safra. Portanto a função de Ano Safra que está sendo criada em `data.py` pode ser reutilizada (com `semestre_ini`), e a env var de alternância (safra × civil) vale também para o MDCR: o ano civil sai do ano do semestre e a safra da regra da seção 4.3. Testes de borda: semestre `06-01` de um ano e `12-01` do ano anterior ficam em safras diferentes; `12-01` de Y e `06-01` de Y+1 ficam na mesma safra. Lembrar que a Safra 22/23 está incompleta e a 26/27 está em curso; a UI deve sinalizar "parcial".

### 5.3 Modelagem no warehouse

1. **Tabela base** `mdcr_semestre` (formato largo, tipada e limpa), com as colunas originais convertidas e as derivadas da seção 4.3 e uma coluna de procedência (arquivo e data do download).
2. **Visão/tabela longa** `mdcr_finalidade` por unpivot das quatro finalidades, com colunas `finalidade`, `area`, `qtde` e `valor` (área nula para comercialização e industrialização). Exemplo de forma:

```sql
SELECT ANO_SEMESTRE_EMISSAO, UF, COD_MUNICIPIO_IBGE, PRODUTO, PROGRAMA,
       'Custeio' AS finalidade, CUSTEIO_AREA AS area, CUSTEIO_QTDE AS qtde, CUSTEIO_VALOR AS valor
FROM mdcr_semestre
UNION ALL
SELECT ANO_SEMESTRE_EMISSAO, UF, COD_MUNICIPIO_IBGE, PRODUTO, PROGRAMA,
       'Investimento', INVESTIMENTO_AREA, INVESTIMENTO_QTDE, INVESTIMENTO_VALOR
FROM mdcr_semestre
-- … comercialização e industrialização (area NULL)
```

3. **Marts** `mart_mdcr_*` no mesmo padrão dos atuais (por `ano_safra`/`ano` e `finalidade`), por exemplo: por UF × programa, por produto × fonte, por município (apenas linhas com código IBGE).
4. **Dimensões** pequenas e reutilizáveis: UF (nome → sigla → região), programa, fonte de recurso (fonte × classe) e produto. Se o `credito` já tiver essas dimensões, reaproveitar e criar apenas o de-para de nomes.

### 5.4 Camada de aplicação

- `data.py`: novas funções de consulta ao MDCR, com a mesma assinatura de filtros (safras/anos, finalidade) das funções atuais, para as abas reutilizarem o filtro de sidebar.
- `abas/`: a nova fonte permite visões que o `credito` não tem ou não tem no mesmo grão: por programa/subprograma, fonte de recurso, produto e município. Uma aba nova (ou seção em aba existente) consome apenas as funções do MDCR.
- Avisos de UI: período parcial, município disponível só em parte dos registros e a diferença de grão (semestral × mensal).

### 5.5 Qualidade e conferência

- Conferir `TOTAL_*` = soma das finalidades e a unicidade da chave de agregação.
- Reconciliar semestre × UF × finalidade com o `credito` e registrar tolerância. Diferenças são esperadas se as fontes têm critérios distintos ou se o MDCR foi revisado depois do download.
- Guardar a data de download e o nome do arquivo de cada carga, porque os dados do BCB são atualizados mensalmente e podem mudar entre downloads.

### 5.6 Riscos

| Risco | Mitigação |
| --- | --- |
| Município nulo em \~75% das linhas | Medir o peso em valor; se alto, não prometer análise municipal completa. |
| Divergência de totais com o `credito` | Camada de conferência e documentação das diferenças de critério. |
| Nomes de produto/programa mudando entre semestres | Normalizar (caixa, espaços) e manter de-para; testar domínios por semestre. |
| Safra 22/23 e 26/27 parciais | Baixar o 2º semestre de 2022 se precisar da Safra 22/23 completa; sinalizar "parcial" na UI. |
| Valores extremos em uma linha | Listar as maiores linhas e validar antes de publicar. |

## 6. Análise do warehouse e recomendação

Os valores do MDCR coincidem com os do `credito`, e a convenção do semestre está confirmada (`06-01` = jan–jun, `12-01` = jul–dez). Base do warehouse analisada em 21/10/2026: `credito` com 10.716.843 linhas, de 2022-01 a 2026-09, em 6 safras (21/22 a 26/27).

### 6.1 Conferência de valores

De 2023-S1 a 2025-S1, o valor por semestre e finalidade é idêntico nas duas bases (R$ bi, três casas). As diferenças (MDCR menos `credito`) aparecem só nos semestres mais recentes:

| Semestre | Custeio | Investimento | Comercialização | Industrialização |
| --- | --- | --- | --- | --- |
| 2025-S2 | 0,000 | −0,001 | 0,000 | 0,000 |
| 2026-S1 | 0,000 | −0,009 | 0,000 | 0,000 |
| 2026-S2 (parcial) | −0,099 | −0,200 | −0,046 | −0,002 |

Hipótese a confirmar: o BCB revisa e completa os meses recentes entre um download e outro. `TOTAL_VALOR` também fecha com a soma das quatro finalidades no agregado por semestre (R$ 198,606 bi em 2025-S2); o teste por linha segue pendente.

**A quantidade de contratos não bate com contratos distintos.** A soma de `*_QTDE` do MDCR supera `count(distinct ref_bacen)` do `credito`. Em 2023-S1: custeio 382.809 × 375.990, investimento 425.316 × 328.178, comercialização 17.237 × 17.159, industrialização 576 × 576. Provavelmente um contrato com vários itens entra em mais de uma linha do MDCR (agrupado por produto, município e programa). Na dashboard, rotular como "contratos-item", não como contratos.

### 6.2 Alinhamento das dimensões

| Dimensão | `credito` | MDCR | Ação |
| --- | --- | --- | --- |
| UF | sigla (27) | nome por extenso (27) | de-para nome → sigla |
| Finalidade | 4 rótulos com acento | 4 grupos de colunas | unpivot usando os mesmos 4 rótulos |
| Programa | 14 valores, caixa mista | 14 valores, caixa alta | comparar com `upper()`; o ABC tem aspas diferentes nas amostras |
| Fonte de recurso | 22 valores, parte em caixa mista | 22 valores | comparar com `upper()` e `trim` |
| Produto | 371 valores | 357 valores | comparar os conjuntos: 14 a mais no `credito` |
| Município | código IBGE, `VARCHAR` | código IBGE com espaços | `trim` e manter como texto |
| Período | `ano`, `ano_safra` (`Safra AA/AA`) | `ANO_SEMESTRE_EMISSAO` | `ANO_SAFRA_SQL` e ano do semestre |
| Porte | 3 valores | não existe | sem equivalente |
| Atividade, modalidade, subprograma, área | não existem | existem | novidades do MDCR |

Cobertura de safra: o `credito` vai da Safra 21/22 (parcial) à 26/27 (até set/2026); o MDCR baixado vai da 22/23 (parcial) à 26/27. Safras completas nas duas bases: 23/24, 24/25 e 25/26. Município vazio: 19,1% das linhas e 62,13% do valor no `credito`; 75,38% das linhas no MDCR (peso em valor ainda não medido).

### 6.3 Recomendação de integração

1. **Conferência automática (prioridade 1).** Comparar `mdcr_semestre` com `credito` por semestre × finalidade (e UF) a cada build, com tolerância definida (o semestre corrente tem diferença maior) e aviso quando estourar. Pode alimentar uma seção de qualidade de dados na dashboard.
2. **Dimensões novas (prioridade 2).** Área financiada de custeio e investimento por safra (hoje só existe `AreaCusteio`/`AreaInvestimento` em `perfil_tomador`, no grão anual civil), atividade, modalidade e subprograma.
3. **Não duplicar o que o `credito` já tem.** Os marts do MDCR devem carregar só o que é novo e evitar município: o `mart_share_uf` já tem 181 mil linhas e o MDCR bruto tem 1,6 milhão.
4. **Pipeline no padrão do `perfil_tomador`.** Um `ingest` gera `data/mdcr.parquet`; o `build_warehouse.py` carrega `mdcr_semestre` (com aviso se o arquivo faltar) e chama uma `_materializar_marts_mdcr` com colunas `granularidade`, `periodo`, `finalidade` e `k`.
5. **Período.** `ANO_SAFRA_SQL` sobre `CAST(ANO_SEMESTRE_EMISSAO AS DATE)` e ano civil do semestre, com as mesmas `granularidade`/`periodo` dos outros marts. Diferente do `perfil_tomador`, o MDCR tem linhas `safra` exatas, sem aproximação.
6. **Decisões em aberto:** baixar o MDCR de 2022 (completa a Safra 22/23) e definir se o escopo é só validação e dimensões novas ou uma aba completa.

