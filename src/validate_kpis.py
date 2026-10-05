"""Run sql/05_kpi_validation_queries.sql and write outputs/kpi_validation.md.

Each query block is introduced by a line "-- @kpi <id> | <name> | <what it shows>".

Usage: python -m src.validate_kpis
"""

from __future__ import annotations

import re
from datetime import date

import pandas as pd
from sqlalchemy import create_engine, text

from src import config

SCRIPT = config.SQL / "05_kpi_validation_queries.sql"
OUTPUT = config.OUTPUTS / "kpi_validation.md"
HEADER = re.compile(r"^-- @kpi (.+?) \| (.+?) \| (.+)$", re.MULTILINE)


def blocks(script: str):
    heads = list(HEADER.finditer(script))
    for i, head in enumerate(heads):
        end = heads[i + 1].start() if i + 1 < len(heads) else len(script)
        yield head.group(1), head.group(2), head.group(3), script[head.end():end].strip()


def to_markdown(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "_No rows: the layer is not loaded._"
    frame = frame.astype(object).where(frame.notna(), "NULL")
    header = "| " + " | ".join(frame.columns) + " |"
    rule = "|" + "---|" * len(frame.columns)
    rows = ["| " + " | ".join(str(v) for v in row) + " |" for row in frame.itertuples(index=False)]
    return "\n".join([header, rule, *rows])


def main() -> None:
    engine = create_engine(config.database_url())
    script = SCRIPT.read_text(encoding="utf-8")
    lines = [
        "# KPI validation",
        "",
        f"Results of `sql/05_kpi_validation_queries.sql` run against the warehouse on "
        f"{date.today().isoformat()}. Every value below comes from `dw` tables and views.",
    ]
    with engine.connect() as conn:
        for kpi_id, name, what, sql in blocks(script):
            frame = pd.read_sql(text(sql.rstrip(";")), conn)
            title = f"KPI {kpi_id} — {name}" if kpi_id[0].isdigit() else name
            lines += ["", f"## {title}", "", f"*{what}*", "", to_markdown(frame)]
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"KPI validation written to {OUTPUT.relative_to(config.ROOT)}")


if __name__ == "__main__":
    main()
