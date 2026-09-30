"""Extract crime incidents into a fixed layout.

This is the only module that knows the crime source. Whatever the origin, the output
has the same columns, so replacing the source means editing CRIME_SOURCE below (or the
reader) and nothing downstream.

Output: data/processed/crime_extract.parquet, one row per incident.

Usage: python -m src.extract_crime
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd

from src import config

OUTPUT = config.DATA_PROCESSED / "crime_extract.parquet"

OUTPUT_COLUMNS = [
    "source_incident_id",
    "latitude",
    "longitude",
    "crime_type",
    "incident_date",
    "incident_hour",
    "location_precision",
    "source_name",
]

# Description of the raw file. `columns` maps output names to source column names;
# use None when the source does not provide the attribute.
CRIME_SOURCE = {
    "source_name": "crime_incidents",
    "path": config.DATA_RAW / "crime" / "incidents.csv",
    "encoding": "utf-8",
    "location_precision": "point",
    "columns": {
        "source_incident_id": None,
        "latitude": "latitud",
        "longitude": "longitud",
        "crime_type": "delito",
        "incident_date": "fecha",
        "incident_hour": "hora",
    },
}


def _row_hash(row: pd.Series) -> str:
    text = "|".join("" if pd.isna(v) else str(v) for v in row.values)
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def _hour(values: pd.Series) -> pd.Series:
    """Hour of day (0-23) from values such as '14', '14:30' or '14:30:00'."""
    hours = pd.to_numeric(values.astype("string").str.extract(r"^\s*(\d{1,2})")[0], errors="coerce")
    return hours.where(hours.between(0, 23)).astype("Int64")


def extract(source: dict | None = None) -> pd.DataFrame:
    """Read the raw crime file and return it in the fixed output layout."""
    source = source or CRIME_SOURCE
    path = Path(source["path"])
    if not path.exists():
        raise FileNotFoundError(
            f"Crime source not found: {path}. Place the georeferenced incident file there "
            "and describe its columns in CRIME_SOURCE."
        )
    raw = pd.read_csv(path, dtype=str, encoding=source.get("encoding", "utf-8"))
    cols = source["columns"]

    out = pd.DataFrame(index=raw.index)
    if cols.get("source_incident_id"):
        out["source_incident_id"] = raw[cols["source_incident_id"]].astype("string").str.strip()
    else:
        ordinal = raw.groupby(list(raw.columns), dropna=False).cumcount().astype(str)
        out["source_incident_id"] = pd.concat([raw, ordinal.rename("_n")], axis=1).apply(_row_hash, axis=1)

    out["latitude"] = pd.to_numeric(raw[cols["latitude"]], errors="coerce")
    out["longitude"] = pd.to_numeric(raw[cols["longitude"]], errors="coerce")
    out["crime_type"] = raw[cols["crime_type"]].astype("string").str.strip().str.upper()

    if cols.get("incident_date"):
        out["incident_date"] = pd.to_datetime(raw[cols["incident_date"]], errors="coerce").dt.date
    else:
        out["incident_date"] = None
    if cols.get("incident_hour"):
        out["incident_hour"] = _hour(raw[cols["incident_hour"]])
    else:
        out["incident_hour"] = pd.array([pd.NA] * len(raw), dtype="Int64")

    out["location_precision"] = source["location_precision"]
    out["source_name"] = source["source_name"]
    return out[OUTPUT_COLUMNS].reset_index(drop=True)


def main() -> None:
    frame = extract()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(OUTPUT, index=False)
    print(f"{len(frame):,} incidents written to {OUTPUT.relative_to(config.ROOT)}")


if __name__ == "__main__":
    main()
