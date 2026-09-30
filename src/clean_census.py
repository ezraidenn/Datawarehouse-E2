"""Clean the 2020 census results at urban AGEB level.

Input : census file with one row per block plus total rows per AGEB, locality,
        municipality and state.
Output: data/processed/census_ageb.parquet, one row per urban AGEB of Mérida.

Change of grain: only the AGEB total rows published by INEGI are kept (MZA = '000').
Blocks are not summed, because block values withheld for confidentiality would make
the sums fall short of the published AGEB totals.
"""

from __future__ import annotations

import pandas as pd

from src import config

OUTPUT = config.DATA_PROCESSED / "census_ageb.parquet"

# source variable -> warehouse column
MEASURES = {
    "POBTOT": "pop_total",
    "POB0_14": "pop_0_14",
    "POB15_64": "pop_15_64",
    "POB65_MAS": "pop_65_plus",
    "P_12YMAS": "pop_12_plus",
    "PEA": "pop_econ_active",
    "POCUPADA": "pop_employed",
    "VIVTOT": "dwellings_total",
    "TVIVHAB": "dwellings_inhabited",
    "PROM_OCUP": "avg_occupants",
}
INTEGER_COLUMNS = [c for c in MEASURES.values() if c != "avg_occupants"]


def source_file():
    folder = config.DATA_RAW / "census" / "extracted"
    return next(folder.rglob("conjunto_de_datos_ageb_urbana_31_cpv2020.csv"))


def clean() -> pd.DataFrame:
    raw = pd.read_csv(source_file(), dtype=str, encoding="utf-8")
    ageb = raw[
        (raw["ENTIDAD"] == config.STATE_CODE)
        & (raw["MUN"] == config.MUNICIPALITY_CODE)
        & (raw["LOC"] != "0000")
        & (raw["AGEB"] != "0000")
        & (raw["MZA"] == "000")
    ].copy()

    out = pd.DataFrame({
        "cvegeo": ageb["ENTIDAD"] + ageb["MUN"] + ageb["LOC"] + ageb["AGEB"],
    })
    # '*' marks values withheld for confidentiality and 'N/D' values not available:
    # both become missing, never zero.
    for source, target in MEASURES.items():
        out[target] = pd.to_numeric(ageb[source], errors="coerce")
    out["has_suppressed"] = out[list(MEASURES.values())].isna().any(axis=1)
    for column in INTEGER_COLUMNS:
        out[column] = out[column].astype("Int64")

    if out["cvegeo"].duplicated().any():
        raise ValueError("duplicate AGEB keys in the census file")
    return out.sort_values("cvegeo").reset_index(drop=True)


def main() -> None:
    frame = clean()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(OUTPUT, index=False)
    print(f"census: {len(frame):,} urban AGEBs, population {int(frame['pop_total'].sum()):,}, "
          f"{int(frame['has_suppressed'].sum())} with withheld values -> {OUTPUT.relative_to(config.ROOT)}")


if __name__ == "__main__":
    main()
