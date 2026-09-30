"""Load the warehouse.

Order:
1. sql/01_schema.sql  - rebuild the staging and dw schemas
2. staging.*          - load the processed tables from Python
3. sql/02_load.sql    - populate dimensions and facts from staging
4. sql/03_views.sql   - KPI views
5. sql/04_validation.sql - checks; any FAIL stops the pipeline with a non-zero exit code
"""

from __future__ import annotations

import json
import sys

import geopandas as gpd
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from src import config
from src.clean_denue import SIZE_CLASSES
from src.spatial_join import CRIME_OUT, ESTABLISHMENTS_OUT, GEOGRAPHY, UNMATCHED_OUT

LAYERS = {"census": "demographic", "denue": "economic", "geography": "geographic",
          "crime": "public_safety"}
VALIDATION_OUT = config.OUTPUTS / "load_validation.json"


def run_sql_file(engine: Engine, name: str) -> None:
    script = (config.SQL / name).read_text(encoding="utf-8")
    # Executed through the raw DBAPI cursor without parameters, so '%' in SQL comments and
    # literals is not taken as a placeholder.
    raw = engine.raw_connection()
    try:
        with raw.cursor() as cursor:
            cursor.execute(script)
        raw.commit()
    finally:
        raw.close()
    print(f"  ran sql/{name}")


def sources_table() -> pd.DataFrame:
    manifest = json.loads(config.SOURCE_MANIFEST.read_text(encoding="utf-8"))
    rows = []
    for code, meta in manifest.items():
        rows.append({
            "source_code": code, "layer": LAYERS[code], "source_name": meta["name"],
            "provider": meta["provider"], "edition": meta["edition"], "url": meta["url"],
            "download_date": meta["download_date"], "original_grain": meta["original_grain"],
            "file_name": meta["file_name"], "sha256": meta["sha256"],
        })
    return pd.DataFrame(rows)


def load_staging(engine: Engine) -> None:
    geography = gpd.read_parquet(GEOGRAPHY)
    census = pd.read_parquet(config.DATA_PROCESSED / "census_ageb.parquet")
    denue_clean = pd.read_parquet(config.DATA_PROCESSED / "denue.parquet")
    establishments = gpd.read_parquet(ESTABLISHMENTS_OUT)
    crime_clean = pd.read_parquet(config.DATA_PROCESSED / "crime.parquet")
    crime = gpd.read_parquet(CRIME_OUT)
    unmatched = pd.read_parquet(UNMATCHED_OUT)

    sources = sources_table()
    if len(crime_clean) == 0:
        sources = sources[sources["source_code"] != "crime"]

    size = pd.DataFrame(
        [(label, order, low, high) for label, (order, low, high) in SIZE_CLASSES.items()],
        columns=["size_label", "size_order", "min_employees", "max_employees"],
    ).astype({"max_employees": "Int64"})

    audit = pd.DataFrame({
        "item": ["census_population", "denue_clean_rows", "crime_clean_rows"],
        "value": [int(census["pop_total"].sum()), len(denue_clean), len(crime_clean)],
    })

    geography.to_postgis("geography", engine, schema="staging", index=False)
    establishments.to_postgis("establishment", engine, schema="staging", index=False)
    crime.to_postgis("crime_incident", engine, schema="staging", index=False)
    census.to_sql("census_ageb", engine, schema="staging", index=False)
    unmatched.to_sql("unmatched_points", engine, schema="staging", index=False)
    sources.to_sql("source", engine, schema="staging", index=False)
    size.to_sql("size_class", engine, schema="staging", index=False)
    audit.to_sql("load_audit", engine, schema="staging", index=False)
    print(f"  staging loaded: {len(geography)} AGEBs, {len(census)} census rows, "
          f"{len(establishments)} establishments, {len(crime)} incidents, {len(unmatched)} unmatched points")


def validate(engine: Engine) -> bool:
    script = (config.SQL / "04_validation.sql").read_text(encoding="utf-8")
    with engine.connect() as conn:
        results = pd.read_sql(text(script), conn)
    for row in results.itertuples():
        detail = f" ({row.detail})" if row.detail else ""
        print(f"  [{row.status}] {row.check_name}{detail}")
    VALIDATION_OUT.parent.mkdir(parents=True, exist_ok=True)
    VALIDATION_OUT.write_text(results.to_json(orient="records", indent=2) + "\n", encoding="utf-8")
    return not (results["status"] == "FAIL").any()


def main() -> int:
    engine = create_engine(config.database_url())
    run_sql_file(engine, "01_schema.sql")
    load_staging(engine)
    run_sql_file(engine, "02_load.sql")
    run_sql_file(engine, "03_views.sql")
    ok = validate(engine)
    print("load: OK" if ok else "load: VALIDATION FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
