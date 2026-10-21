## Análise de dados

### 1. Criar pasta na raiz do projeto
```
/dados
```

### 2. Baixar arquivos do Banco Central e adicionar na pasta criada anteriormente

Link para download: https://www.bcb.gov.br/estabilidadefinanceira/micrrural 

### 3. Executar programa:

```bash
cd dados-dc

python3 -m venv .venv

source .venv/bin/activate

pip install -r requirements.txt

python mdcr_analise.py --files "dados/*" --db warehouse.duckdb --out saida/
```

### Resultados

```
dicionario_dados_result.md
```