"""Generate docs/data_dictionary.md from the warehouse catalog.

Table and column descriptions come from the COMMENT ON statements in sql/01_schema.sql
and sql/03_views.sql, so the dictionary always matches the database.

Usage: python -m src.make_data_dictionary
"""

from __future__ import annotations

import pandas as pd
from sqlalchemy import create_engine, text

from src import config

OUTPUT = config.DOCS / "data_dictionary.md"

OBJECTS = text("""
    SELECT c.relname AS name,
           CASE c.relkind WHEN 'r' THEN 'table' WHEN 'v' THEN 'view' END AS kind,
           obj_description(c.oid, 'pg_class') AS description,
           (SELECT count(*) FROM information_schema.columns
             WHERE table_schema = 'dw' AND table_name = c.relname) AS n_columns
    FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'dw' AND c.relkind IN ('r', 'v')
    ORDER BY CASE WHEN c.relname LIKE 'dim%' THEN 1 WHEN c.relname LIKE 'fact%' THEN 2 ELSE 3 END,
             c.relname
""")

COLUMNS = text("""
    SELECT a.attname AS column_name,
           format_type(a.atttypid, a.atttypmod) AS data_type,
           NOT a.attnotnull AS nullable,
           col_description(c.oid, a.attnum) AS description,
           EXISTS (SELECT 1 FROM pg_constraint k
                   WHERE k.conrelid = c.oid AND k.contype = 'p' AND a.attnum = ANY (k.conkey)) AS pk,
           (SELECT confrelid::regclass::text FROM pg_constraint k
             WHERE k.conrelid = c.oid AND k.contype = 'f' AND a.attnum = ANY (k.conkey) LIMIT 1) AS fk
    FROM pg_attribute a
    JOIN pg_class c ON c.oid = a.attrelid
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'dw' AND c.relname = :name AND a.attnum > 0 AND NOT a.attisdropped
    ORDER BY a.attnum
""")

ROWS = "SELECT count(*) FROM dw.{name}"


def describe_key(row) -> str:
    if row.pk:
        return "PK"
    if isinstance(row.fk, str):
        return f"FK → {row.fk.replace('dw.', '')}"
    return ""


def describe_column(row, known: dict) -> str:
    """Catalog comment; else the comment of a same-named column elsewhere in dw (views that
    repeat KPI columns); else a generic description for surrogate and foreign keys."""
    if isinstance(row.description, str):
        return row.description
    if row.column_name in known:
        return known[row.column_name]
    if row.pk and row.column_name.endswith("_key"):
        return "Surrogate key."
    if isinstance(row.fk, str):
        return f"Reference to {row.fk.replace('dw.', '')}."
    return ""


def main() -> None:
    engine = create_engine(config.database_url())
    lines = [
        "# Data dictionary",
        "",
        "Schema `dw` of the `merida_dw` database. Generated from the database catalog by",
        "`python -m src.make_data_dictionary`; descriptions are the `COMMENT ON` texts of",
        "`sql/01_schema.sql` and `sql/03_views.sql`. The grain of each table is stated in its",
        "description.",
        "",
        "## Contents",
        "",
        "| Object | Type | Rows | Description |",
        "|---|---|---|---|",
    ]
    with engine.connect() as conn:
        objects = pd.read_sql(OBJECTS, conn)
        known = {}
        for name in ["vw_kpi_ageb"] + list(objects["name"]):
            for col in pd.read_sql(COLUMNS, conn, params={"name": name}).itertuples():
                if isinstance(col.description, str):
                    known.setdefault(col.column_name, col.description)
        counts = {name: conn.execute(text(ROWS.format(name=name))).scalar()
                  for name in objects["name"]}
        for obj in objects.itertuples():
            lines.append(f"| [`{obj.name}`](#{obj.name.replace('_', '')}) | {obj.kind} | "
                         f"{counts[obj.name]:,} | {obj.description or ''} |")
        for obj in objects.itertuples():
            columns = pd.read_sql(COLUMNS, conn, params={"name": obj.name})
            lines += ["", f"## {obj.name}", "", f"*{obj.kind}* — {obj.description or ''}", "",
                      "| Column | Type | Key | Null | Description |", "|---|---|---|---|---|"]
            for col in columns.itertuples():
                null = "yes" if col.nullable and obj.kind == "table" else ("" if obj.kind == "view" else "no")
                lines.append(f"| `{col.column_name}` | {col.data_type} | {describe_key(col)} | "
                             f"{null} | {describe_column(col, known)} |")
    OUTPUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"data dictionary written to {OUTPUT.relative_to(config.ROOT)}")


if __name__ == "__main__":
    main()
