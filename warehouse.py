#!/usr/bin/env python3
"""Diagnóstico do warehouse SICOR e conferência com o MDCR.

Uso:
  python diagnostico_warehouse.py warehouse_copy.duckdb "dados/*.csv" > diagnostico.txt

O 2º argumento (CSVs do MDCR) é opcional. Abre o banco em modo somente leitura.
"""
import glob
import sys

import duckdb
import pandas as pd

db = sys.argv[1]
csv_glob = sys.argv[2] if len(sys.argv) > 2 else None
c = duckdb.connect(db, read_only=True)

print("== tabelas e contagens ==")
for (t,) in c.execute(
        "select table_name from information_schema.tables where table_schema='main' order by 1").fetchall():
    print(t, c.execute(f'select count(*) from "{t}"').fetchone()[0])

print("\n== colunas ==")
for t in ["credito", "perfil_tomador"]:
    try:
        print(t, [(r[0], r[1]) for r in c.execute(f'describe "{t}"').fetchall()])
    except Exception as e:  # noqa: BLE001
        print(t, "erro:", e)

print("\n== credito: periodo ==")
print(c.execute("select min(ano), max(ano), min(competencia), max(competencia) from credito").fetchall())
print(c.execute("select ano_safra, count(*), round(sum(valor)/1e9, 2) from credito group by 1 order by 1").fetchall())

print("\n== municipio ==")
print("% linhas nulas / % valor nulo:", c.execute(
    "select round(100*avg((municipio is null)::int),2), "
    "round(100*sum(valor) filter (where municipio is null)/sum(valor),2) from credito").fetchall())
print("amostra:", c.execute(
    "select distinct municipio from credito where municipio is not null limit 5").fetchall())

print("\n== dimensoes (distintos e amostras) ==")
for col in ["uf", "finalidade", "programa", "fonte", "porte"]:
    vals = [v[0] for v in c.execute(f"select distinct {col} from credito order by 1").fetchall()]
    print(f"{col} ({len(vals)}):", vals[:60])
n_prod = c.execute("select count(distinct produto) from credito").fetchone()[0]
print(f"produto ({n_prod}):", [v[0] for v in c.execute(
    "select distinct produto from credito order by 1 limit 40").fetchall()])

print("\n== credito por semestre x finalidade (valor em R$ bi, contratos distintos) ==")
for r in c.execute("""
    select ano || case when cast(substr(competencia,6,2) as int) <= 6 then '-S1' else '-S2' end as semestre,
           finalidade, round(sum(valor)/1e9, 3) as valor_bi, count(distinct ref_bacen) as contratos
    from credito group by 1, 2 order by 1, 2""").fetchall():
    print(r)

if csv_glob:
    def num(s):
        return pd.to_numeric(s.astype(str).str.strip().str.replace(",", ".", regex=False), errors="coerce")

    frames = []
    for p in sorted(glob.glob(csv_glob)):
        for enc in ("utf-8-sig", "latin-1"):
            try:
                frames.append(pd.read_csv(p, sep=";", encoding=enc, dtype=str))
                break
            except Exception:  # noqa: BLE001
                continue
    m = pd.concat(frames, ignore_index=True)
    print("\n== MDCR por semestre x finalidade (valor em R$ bi, soma de QTDE) ==")
    for fin in ["CUSTEIO", "INVESTIMENTO", "COMERCIALIZACAO", "INDUSTRIALIZACAO"]:
        g = pd.DataFrame({
            "semestre": m["ANO_SEMESTRE_EMISSAO"],
            "valor_bi": num(m[f"{fin}_VALOR"]) / 1e9,
            "qtde": num(m[f"{fin}_QTDE"]),
        }).groupby("semestre").sum().round(3)
        print(fin)
        print(g.to_string())
    print("\nTOTAL_VALOR por semestre (R$ bi):")
    print((num(m["TOTAL_VALOR"]).groupby(m["ANO_SEMESTRE_EMISSAO"]).sum() / 1e9).round(3).to_string())