"""Clean the DENUE establishments of the municipality of Mérida.

Input : data/raw/denue/extracted/conjunto_de_datos/denue_inegi_31_.csv (Yucatán, Latin-1)
Output: data/processed/denue.parquet, one row per establishment

The grain does not change. Establishments are filtered to the municipality, duplicate ids
are removed, coordinates are validated and the sector attributes used by the KPIs are derived.
"""

from __future__ import annotations

import pandas as pd

from src import config, scian

SOURCE = config.DATA_RAW / "denue" / "extracted" / "conjunto_de_datos" / "denue_inegi_31_.csv"
OUTPUT = config.DATA_PROCESSED / "denue.parquet"

# Generous bounding box around the municipality, used only to reject impossible coordinates.
LAT_RANGE = (20.6, 21.3)
LON_RANGE = (-90.0, -89.3)

# Employment strata as published in `per_ocu`: label -> (order, minimum, maximum)
SIZE_CLASSES = {
    "0 a 5 personas": (1, 0, 5),
    "6 a 10 personas": (2, 6, 10),
    "11 a 30 personas": (3, 11, 30),
    "31 a 50 personas": (4, 31, 50),
    "51 a 100 personas": (5, 51, 100),
    "101 a 250 personas": (6, 101, 250),
    "251 y más personas": (7, 251, None),
}


def clean() -> tuple[pd.DataFrame, dict]:
    raw = pd.read_csv(SOURCE, dtype=str, encoding="latin-1")
    report = {"rows_state": len(raw)}

    frame = raw[(raw["cve_ent"] == config.STATE_CODE) & (raw["cve_mun"] == config.MUNICIPALITY_CODE)].copy()
    report["rows_municipality"] = len(frame)

    duplicated = frame["id"].duplicated()
    report["duplicate_ids_removed"] = int(duplicated.sum())
    frame = frame[~duplicated]

    frame["latitude"] = pd.to_numeric(frame["latitud"], errors="coerce")
    frame["longitude"] = pd.to_numeric(frame["longitud"], errors="coerce")
    valid = (
        frame["latitude"].between(*LAT_RANGE) & frame["longitude"].between(*LON_RANGE)
    )
    report["invalid_coordinates_removed"] = int((~valid).sum())
    frame = frame[valid]

    unknown_size = ~frame["per_ocu"].isin(SIZE_CLASSES)
    if unknown_size.any():
        raise ValueError(f"unexpected size classes: {sorted(frame.loc[unknown_size, 'per_ocu'].unique())}")

    out = pd.DataFrame({
        "denue_id": frame["id"],
        "establishment_name": frame["nom_estab"].str.strip(),
        "scian_code": frame["codigo_act"].str.strip(),
        "activity_name": frame["nombre_act"].str.strip(),
        "size_label": frame["per_ocu"],
        "denue_cvegeo": frame["cve_ent"] + frame["cve_mun"] + frame["cve_loc"] + frame["ageb"],
        "registration_month": frame["fecha_alta"],
        "latitude": frame["latitude"],
        "longitude": frame["longitude"],
    })
    out["sector_code"] = out["scian_code"].map(scian.sector_code)
    out["sector_name"] = out["scian_code"].map(scian.sector_name)
    out["sector_group"] = out["scian_code"].map(scian.sector_group)

    unknown_sector = out["sector_name"] == "Unknown"
    if unknown_sector.any():
        raise ValueError(f"unmapped SCIAN sectors: {sorted(out.loc[unknown_sector, 'sector_code'].unique())}")

    report["rows_clean"] = len(out)
    return out.sort_values("denue_id").reset_index(drop=True), report


def main() -> None:
    frame, report = clean()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(OUTPUT, index=False)
    print(f"denue: {report} -> {OUTPUT.relative_to(config.ROOT)}")


if __name__ == "__main__":
    main()
