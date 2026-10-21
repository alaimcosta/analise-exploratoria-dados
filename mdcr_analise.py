#!/usr/bin/env python3
"""Perfila arquivos MDCR (Banco Central) e o warehouse.duckdb.

Uso:
  python mdcr_analise.py --files "dados/*.csv" --db warehouse.duckdb --out saida/
  (aceita .csv, .xlsx, .xls; use --skiprows se o arquivo tiver linhas de título antes do cabeçalho)

Gera em --out:
  dicionario_dados.csv / .md   -> colunas, tipo, nulos, distintos, min/max, exemplos (coluna 'descricao' para preencher)
  warehouse_schema.md          -> tabelas, colunas, contagens e faixa temporal do warehouse
  integracao_sugerida.md       -> colunas em comum (join keys) e cobertura de valores entre MDCR e tabelas do warehouse
"""
import argparse
import glob
import os
import re
import unicodedata

import pandas as pd


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")


def read_any(path: str, skiprows: int) -> pd.DataFrame:
    if path.lower().endswith((".xlsx", ".xls")):
        df = pd.read_excel(path, skiprows=skiprows, dtype=str)
    else:
        last = None
        for enc in ("utf-8-sig", "latin-1"):
            for sep in (";", ",", "\t"):
                try:
                    df = pd.read_csv(path, sep=sep, encoding=enc, skiprows=skiprows, dtype=str)
                    if df.shape[1] > 1:
                        df["_arquivo"] = os.path.basename(path)
                        return df
                except Exception as e:  # noqa: BLE001
                    last = e
        raise RuntimeError(f"Não consegui ler {path}: {last}")
    df["_arquivo"] = os.path.basename(path)
    return df


def to_num(s: pd.Series) -> pd.Series:
    """Converte '1.234,56' ou '1234.56' em número; devolve NaN onde não der."""
    t = s.dropna().astype(str).str.strip()
    if t.empty:
        return pd.to_numeric(s, errors="coerce")
    br = t.str.contains(r"\d,\d").mean() > 0.5
    x = s.astype(str).str.strip()
    if br:
        x = x.str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
    return pd.to_numeric(x, errors="coerce")


def profile(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for c in df.columns:
        s = df[c]
        non_null = s.dropna()
        num = to_num(s)
        is_num = len(non_null) > 0 and num.notna().sum() / len(non_null) > 0.95
        rows.append({
            "coluna": c,
            "tipo_inferido": "numerico" if is_num else "texto",
            "nulos": int(s.isna().sum()),
            "pct_nulos": round(100 * s.isna().mean(), 2),
            "distintos": int(s.nunique()),
            "min": num.min() if is_num else (non_null.min() if len(non_null) else None),
            "max": num.max() if is_num else (non_null.max() if len(non_null) else None),
            "exemplos": " | ".join(map(str, non_null.drop_duplicates().head(5))),
            "descricao": "",
        })
    return pd.DataFrame(rows)


def warehouse_report(db: str, out: str):
    import duckdb

    con = duckdb.connect(db, read_only=True)
    tables = [r[0] for r in con.execute(
        "select table_name from information_schema.tables where table_schema='main' order by 1").fetchall()]
    lines = ["# Schema do warehouse\n"]
    schema = {}
    for t in tables:
        cols = con.execute(f'describe "{t}"').fetchall()
        n = con.execute(f'select count(*) from "{t}"').fetchone()[0]
        schema[t] = [c[0] for c in cols]
        lines.append(f"## `{t}` ({n:,} linhas)\n\n| coluna | tipo |\n|---|---|")
        lines += [f"| {c[0]} | {c[1]} |" for c in cols]
        for tc in [c[0] for c in cols if norm(c[0]) in ("competencia", "ano", "ano_safra", "semestre", "data")]:
            mn, mx = con.execute(f'select min("{tc}"), max("{tc}") from "{t}"').fetchone()
            lines.append(f"\n_Faixa de `{tc}`: {mn} → {mx}_")
        lines.append("")
    with open(os.path.join(out, "warehouse_schema.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return con, schema


def integration_report(mdcr: pd.DataFrame, con, schema: dict, out: str):
    mcols = {norm(c): c for c in mdcr.columns if c != "_arquivo"}
    lines = ["# Integração sugerida MDCR × warehouse\n",
             "Colunas em comum (por nome normalizado) e cobertura dos valores do MDCR no warehouse.\n"]
    for t, cols in schema.items():
        common = [(mcols[norm(c)], c) for c in cols if norm(c) in mcols]
        if not common:
            continue
        lines.append(f"## `{t}`\n\n| coluna MDCR | coluna warehouse | distintos MDCR | % cobertos no warehouse |\n|---|---|---|---|")
        for mc, wc in common:
            m_vals = set(mdcr[mc].dropna().astype(str).str.strip().str.upper())
            try:
                w_vals = {str(r[0]).strip().upper() for r in con.execute(
                    f'select distinct "{wc}" from "{t}" where "{wc}" is not null').fetchall()}
            except Exception:  # noqa: BLE001
                continue
            cov = 100 * len(m_vals & w_vals) / len(m_vals) if m_vals else 0
            lines.append(f"| {mc} | {wc} | {len(m_vals)} | {cov:.1f}% |")
        lines.append("")
    if len(lines) == 2:
        lines.append("_Nenhuma coluna com nome equivalente encontrada; mapear manualmente._")
    with open(os.path.join(out, "integracao_sugerida.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--files", required=True)
    ap.add_argument("--db")
    ap.add_argument("--out", default="saida")
    ap.add_argument("--skiprows", type=int, default=0)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    paths = sorted(glob.glob(a.files))
    if not paths:
        raise SystemExit(f"Nenhum arquivo encontrado em {a.files}")
    mdcr = pd.concat([read_any(p, a.skiprows) for p in paths], ignore_index=True)
    print(f"{len(paths)} arquivo(s), {len(mdcr):,} linhas, {mdcr.shape[1]} colunas")

    prof = profile(mdcr)
    prof.to_csv(os.path.join(a.out, "dicionario_dados.csv"), index=False, encoding="utf-8-sig")
    with open(os.path.join(a.out, "dicionario_dados.md"), "w", encoding="utf-8") as f:
        f.write("# Dicionário de dados — MDCR\n\n")
        f.write(f"Arquivos: {', '.join(os.path.basename(p) for p in paths)}\n\n")
        f.write(prof.to_markdown(index=False) if hasattr(prof, "to_markdown") else prof.to_string(index=False))

    if a.db:
        con, schema = warehouse_report(a.db, a.out)
        integration_report(mdcr, con, schema, a.out)
    print("Saída em", a.out)


if __name__ == "__main__":
    main()
