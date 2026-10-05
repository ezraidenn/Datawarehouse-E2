"""Clean the SESNSP municipal crime incidence for Mérida.

Input : data/raw/crime_municipal/IDM_NM_dic25.csv (every municipality of Mexico, Latin-1;
        one row per municipality, year and crime modality, one column per month)
Output: data/processed/crime_municipal.parquet, one row per month and crime modality

Change of grain: the twelve month columns are unpivoted into rows. The geography stays at
municipality level: the source publishes no location, so these incidents cannot be assigned
to AGEBs. Crime groups are the source's own "bien jurídico afectado", translated.
"""

from __future__ import annotations

import pandas as pd

from src import config

SOURCE = config.DATA_RAW / "crime_municipal" / "IDM_NM_dic25.csv"
OUTPUT = config.DATA_PROCESSED / "crime_municipal.parquet"
MUNICIPALITY_KEY = str(int(config.STATE_MUN))  # the source drops leading zeros: 31050

MONTHS = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto",
          "Septiembre", "Octubre", "Noviembre", "Diciembre"]
LEGAL_GOOD = {
    "La vida y la Integridad corporal": "Life and bodily integrity",
    "Libertad personal": "Personal liberty",
    "La libertad y la seguridad sexual": "Sexual freedom and safety",
    "El patrimonio": "Property",
    "La familia": "Family",
    "La sociedad": "Society",
    "Otros bienes jurídicos afectados (del fuero común)": "Other",
}
COLUMNS = ["year", "month", "date_key", "municipality_cvegeo", "legal_good", "crime_group",
           "crime_category", "crime_type", "modality", "incidents"]


def empty() -> pd.DataFrame:
    return pd.DataFrame({c: pd.Series(dtype="int64" if c in {"year", "month", "date_key", "incidents"}
                                      else "object") for c in COLUMNS})


def clean() -> tuple[pd.DataFrame, dict]:
    parts = []
    for chunk in pd.read_csv(SOURCE, encoding="latin-1", dtype=str, chunksize=500_000):
        parts.append(chunk[chunk["Cve. Municipio"].str.strip() == MUNICIPALITY_KEY])
    raw = pd.concat(parts, ignore_index=True)
    report = {"rows_municipality": len(raw)}

    unknown = set(raw["Bien jurídico afectado"]) - set(LEGAL_GOOD)
    if unknown:
        raise ValueError(f"unmapped legal goods: {sorted(unknown)}")

    long = raw.melt(
        id_vars=["Año", "Bien jurídico afectado", "Tipo de delito", "Subtipo de delito", "Modalidad"],
        value_vars=MONTHS, var_name="month_name", value_name="incidents",
    )
    out = pd.DataFrame({
        "year": long["Año"].astype(int),
        "month": long["month_name"].map({m: i for i, m in enumerate(MONTHS, start=1)}),
        "municipality_cvegeo": config.STATE_MUN,
        "legal_good": long["Bien jurídico afectado"].str.strip(),
        "crime_category": long["Tipo de delito"].str.strip(),
        "crime_type": long["Subtipo de delito"].str.strip().str.upper(),
        "modality": long["Modalidad"].str.strip(),
        "incidents": pd.to_numeric(long["incidents"], errors="coerce"),
    })
    report["missing_counts"] = int(out["incidents"].isna().sum())
    out = out.dropna(subset=["incidents"])
    out["incidents"] = out["incidents"].astype(int)
    out["crime_group"] = out["legal_good"].map(LEGAL_GOOD)
    out["date_key"] = out["year"] * 10000 + out["month"] * 100 + 1

    if out.duplicated(subset=["date_key", "crime_type", "modality"]).any():
        raise ValueError("duplicate month x crime type x modality rows")
    report["rows_clean"] = len(out)
    report["incidents_total"] = int(out["incidents"].sum())
    return out[COLUMNS].sort_values(["date_key", "crime_type", "modality"]).reset_index(drop=True), report


def main() -> None:
    config.DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    if not SOURCE.exists():
        print("crime (municipal): source file not found, writing an empty table")
        empty().to_parquet(OUTPUT, index=False)
        return
    frame, report = clean()
    frame.to_parquet(OUTPUT, index=False)
    print(f"crime (municipal): {report} -> {OUTPUT.relative_to(config.ROOT)}")


if __name__ == "__main__":
    main()
