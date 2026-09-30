"""Clean the crime incidents produced by the extract step.

Input : data/processed/crime_extract.parquet (fixed layout, see src/extract_crime.py)
Output: data/processed/crime.parquet, one row per incident

The grain does not change. Incidents without usable coordinates are dropped and counted,
exact duplicates (same place, type, date and hour) are collapsed, and the date and time
keys used by the warehouse are derived.
"""

from __future__ import annotations

import pandas as pd

from src import config
from src.clean_denue import LAT_RANGE, LON_RANGE
from src.extract_crime import OUTPUT as EXTRACT, OUTPUT_COLUMNS

OUTPUT = config.DATA_PROCESSED / "crime.parquet"

DUPLICATE_KEY = ["latitude", "longitude", "crime_type", "incident_date", "incident_hour"]

# Harmonised groups, matched on keywords of the published category (first match wins).
CRIME_GROUPS = [
    ("violent", ("HOMICIDIO", "LESION", "FEMINICIDIO", "SECUESTRO", "VIOLACION", "VIOLACIÓN",
                 "ABUSO SEXUAL", "VIOLENCIA", "AMENAZA", "EXTORSION", "EXTORSIÓN")),
    ("property", ("ROBO", "HURTO", "DAÑO", "DANO", "FRAUDE", "DESPOJO", "ABUSO DE CONFIANZA")),
]


def crime_group(crime_type: str) -> str:
    text = str(crime_type).upper()
    for group, keywords in CRIME_GROUPS:
        if any(k in text for k in keywords):
            return group
    return "other"


def empty() -> pd.DataFrame:
    frame = pd.DataFrame(columns=OUTPUT_COLUMNS + ["crime_group", "date_key", "time_key"])
    return frame.astype({"latitude": float, "longitude": float, "date_key": int, "time_key": int})


def clean(extract: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    report = {"rows_extract": len(extract)}
    frame = extract.copy()

    valid = frame["latitude"].between(*LAT_RANGE) & frame["longitude"].between(*LON_RANGE)
    report["invalid_coordinates_removed"] = int((~valid).sum())
    frame = frame[valid]

    duplicated = frame.duplicated(subset=DUPLICATE_KEY, keep="first")
    report["duplicates_removed"] = int(duplicated.sum())
    frame = frame[~duplicated].copy()

    frame["crime_group"] = frame["crime_type"].map(crime_group)
    dates = pd.to_datetime(frame["incident_date"], errors="coerce")
    frame["date_key"] = dates.dt.strftime("%Y%m%d").fillna("0").astype(int)
    frame["time_key"] = frame["incident_hour"].astype("Int64").fillna(-1).astype(int)

    report["rows_clean"] = len(frame)
    return frame.reset_index(drop=True), report


def main() -> None:
    if not EXTRACT.exists():
        print("crime: no extract found, writing an empty table (crime indicators will be unavailable)")
        empty().to_parquet(OUTPUT, index=False)
        return
    frame, report = clean(pd.read_parquet(EXTRACT))
    frame.to_parquet(OUTPUT, index=False)
    print(f"crime: {report} -> {OUTPUT.relative_to(config.ROOT)}")


if __name__ == "__main__":
    main()
