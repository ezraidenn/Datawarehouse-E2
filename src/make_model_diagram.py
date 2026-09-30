"""Draw the warehouse model from the live database catalog.

Outputs:
    docs/warehouse_model.png     full entity-relationship diagram (every table, column, key)
    docs/warehouse_overview.png  overview: dimensions above, facts below, coloured by layer

Requires Graphviz (`dot` on the PATH, or GRAPHVIZ_DOT pointing to the executable).

Usage: python -m src.make_model_diagram
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

from src import config

MODEL_OUT = config.DOCS / "warehouse_model.png"
OVERVIEW_OUT = config.DOCS / "warehouse_overview.png"

CATALOG = text("""
    SELECT c.relname AS tbl, a.attname AS col, format_type(a.atttypid, a.atttypmod) AS typ,
           EXISTS (SELECT 1 FROM pg_constraint k
                   WHERE k.conrelid = c.oid AND k.contype = 'p' AND a.attnum = ANY (k.conkey)) AS pk,
           (SELECT confrelid::regclass::text FROM pg_constraint k
             WHERE k.conrelid = c.oid AND k.contype = 'f' AND a.attnum = ANY (k.conkey) LIMIT 1) AS fk
    FROM pg_attribute a
    JOIN pg_class c ON c.oid = a.attrelid
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'dw' AND c.relkind = 'r' AND a.attnum > 0 AND NOT a.attisdropped
    ORDER BY c.relname, a.attnum
""")

GRAIN = {
    "fact_demographics": "1 row = 1 urban AGEB (Census 2020)",
    "fact_establishment": "1 row = 1 DENUE establishment",
    "fact_crime_incident": "1 row = 1 georeferenced incident",
}
LAYER_COLOUR = {
    "fact_demographics": "#1D91C0",
    "fact_establishment": "#41AB5D",
    "fact_crime_incident": "#EF6548",
}
RIGHT_SIDE = {"dim_crime_type", "dim_date", "dim_time_of_day"}  # drawn right of the facts


def dot_executable() -> str:
    candidate = os.environ.get("GRAPHVIZ_DOT") or shutil.which("dot")
    if not candidate:
        raise SystemExit("Graphviz 'dot' not found: install Graphviz or set GRAPHVIZ_DOT")
    return candidate


def render(source: str, target: Path) -> None:
    with tempfile.NamedTemporaryFile("w", suffix=".dot", delete=False, encoding="utf-8") as fh:
        fh.write(source)
        path = fh.name
    try:
        subprocess.run([dot_executable(), "-Tpng", "-Gdpi=170", path, "-o", str(target)], check=True)
    finally:
        os.unlink(path)
    print(f"diagram written to {target.relative_to(config.ROOT)}")


def short_type(sql_type: str) -> str:
    return (sql_type.replace("character", "char").replace("numeric", "num")
            .replace("geometry(MultiPolygon,4326)", "geometry").replace("geometry(Point,4326)", "geometry"))


def read_catalog():
    engine = create_engine(config.database_url())
    cols = pd.read_sql(CATALOG, engine)
    cols["fk"] = [v.replace("dw.", "") if isinstance(v, str) else None for v in cols["fk"]]
    tables = list(dict.fromkeys(cols["tbl"]))
    facts = [t for t in tables if t.startswith("fact_")]
    dims = [t for t in tables if t.startswith("dim_")]
    edges = [(r.tbl, r.col, r.fk) for r in cols.itertuples() if isinstance(r.fk, str)]
    return cols, facts, dims, edges


def full_model(cols, facts, dims, edges) -> str:
    def table(name: str, head: str, body: str) -> str:
        rows = []
        for r in cols[cols.tbl == name].itertuples():
            label = f"<B>{r.col}</B> 🔑" if r.pk else (f"{r.col} →" if isinstance(r.fk, str) else r.col)
            rows.append(f'<TR><TD ALIGN="LEFT" PORT="{r.col}"><FONT POINT-SIZE="9">{label}</FONT></TD>'
                        f'<TD ALIGN="LEFT" PORT="{r.col}_r"><FONT POINT-SIZE="8" COLOR="#6B7785">{short_type(r.typ)}</FONT></TD></TR>')
        grain = (f'<TR><TD COLSPAN="2" BGCOLOR="{head}"><FONT COLOR="#C7E9B4" POINT-SIZE="8"><I>{GRAIN[name]}</I>'
                 f'</FONT></TD></TR>' if name in GRAIN else "")
        return (f'{name} [label=<<TABLE BORDER="1" COLOR="#9FB3C8" CELLBORDER="0" CELLSPACING="0" '
                f'CELLPADDING="4" BGCOLOR="{body}"><TR><TD COLSPAN="2" BGCOLOR="{head}"><FONT COLOR="white" '
                f'POINT-SIZE="10"><B>{name}</B></FONT></TD></TR>{grain}{"".join(rows)}</TABLE>>];')

    lines = ['digraph model {',
             'graph [rankdir=LR, bgcolor="white", nodesep=0.35, ranksep=1.1, fontname="Helvetica", pad=0.3];',
             'node [shape=plaintext, fontname="Helvetica"];',
             'edge [color="#7A8B99", penwidth=0.9];']
    lines += [table(t, "#225EA8", "#F7FBFF") for t in dims]
    lines += [table(t, "#0B3C5D", "#EAF3F9") for t in facts]
    # One-to-many: the crow's foot marks the "many" end, on the referencing column.
    for t, c, fk in edges:
        if fk in RIGHT_SIDE:
            # edge drawn fact -> dimension so the dimension ranks to the right; the crow's
            # foot is the tail, on the fact side
            lines.append(f'{t}:{c}_r:e -> {fk}:w [dir=back, arrowtail=crow, arrowhead=none];')
        else:
            lines.append(f'{fk}:e -> {t}:{c}:w [arrowhead=crow, arrowtail=none];')
    lines.append('labelloc="t"; label=<<FONT POINT-SIZE="16"><B>Mérida Urban Intelligence · '
                 'Data Warehouse model (schema dw)</B></FONT>>;}')
    return "\n".join(lines)


def overview(facts, dims, edges) -> str:
    lines = ['digraph overview {',
             'graph [rankdir=TB, newrank=true, bgcolor="white", nodesep=0.45, ranksep=1.0, fontname="Helvetica", pad=0.3];',
             'node [shape=box, style="rounded,filled", fontname="Helvetica", fontsize=10, penwidth=0];',
             'edge [color="#9AA5B1", arrowhead=none, penwidth=1.1];',
             'subgraph cluster_dims { label=<<FONT POINT-SIZE="10" COLOR="#5B6773">DIMENSIONS</FONT>>; '
             'labeljust="l"; style="rounded,dashed"; color="#C9D3DD";']
    for t in dims:
        fill, font = ("#225EA8", "white") if t == "dim_geography" else ("#DCE6EF", "#1F2A36")
        lines.append(f'{t} [label="{t}", fillcolor="{fill}", fontcolor="{font}"];')
    lines += ['}', 'subgraph cluster_facts { label=<<FONT POINT-SIZE="10" COLOR="#5B6773">FACTS</FONT>>; '
              'labeljust="l"; labelloc="b"; style="rounded,dashed"; color="#C9D3DD";']
    for t in facts:
        lines.append(f'{t} [label=<<B>{t}</B><BR/><FONT POINT-SIZE="8">{GRAIN[t]}</FONT>>, '
                     f'fillcolor="{LAYER_COLOUR[t]}", fontcolor="white", margin="0.25,0.12"];')
    lines += ['}', '{rank=same; ' + "; ".join(dims) + '}']
    drawn = set()
    for t, _, fk in edges:
        if (t, fk) in drawn:
            continue
        drawn.add((t, fk))
        width = 2.6 if fk == "dim_geography" else 1.2
        lines.append(f'{fk} -> {t} [color="{LAYER_COLOUR.get(t, "#9AA5B1")}", penwidth={width}];')
    lines.append(
        'legend [shape=plaintext, style="", label=<<TABLE BORDER="0" CELLSPACING="4"><TR>'
        '<TD BGCOLOR="#1D91C0" WIDTH="14"></TD><TD ALIGN="LEFT"><FONT POINT-SIZE="9">demographic</FONT></TD>'
        '<TD BGCOLOR="#41AB5D" WIDTH="14"></TD><TD ALIGN="LEFT"><FONT POINT-SIZE="9">economic</FONT></TD>'
        '<TD BGCOLOR="#EF6548" WIDTH="14"></TD><TD ALIGN="LEFT"><FONT POINT-SIZE="9">public safety</FONT></TD>'
        '</TR></TABLE>>];')
    lines.append('labelloc="t"; label=<<FONT POINT-SIZE="15"><B>Constellation schema: three facts share '
                 'the AGEB dimension</B></FONT>>;}')
    return "\n".join(lines)


def main() -> None:
    cols, facts, dims, edges = read_catalog()
    render(full_model(cols, facts, dims, edges), MODEL_OUT)
    render(overview(facts, dims, edges), OVERVIEW_OUT)


if __name__ == "__main__":
    main()
