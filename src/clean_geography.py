"""Clean the urban AGEB polygons of the study area.

Input : data/raw/geography/extracted/conjunto_de_datos/31a.shp (all urban AGEBs of Yucatán)
Output: data/processed/geography.parquet, one row per urban AGEB of the municipality of Mérida

Changes of representation: geometries are reprojected from EPSG:6372 to EPSG:4326 after the
area has been measured in EPSG:6372, and single polygons are stored as MultiPolygon.
"""

from __future__ import annotations

import geopandas as gpd
from shapely.geometry import MultiPolygon

from src import config

LAYER_DIR = config.DATA_RAW / "geography" / "extracted" / "conjunto_de_datos"
OUTPUT = config.DATA_PROCESSED / "geography.parquet"
MUNICIPALITY_OUTPUT = config.DATA_PROCESSED / "municipality.parquet"


def read_layer(name: str) -> gpd.GeoDataFrame:
    """Read a Marco Geoestadístico layer and declare its CRS.

    The .prj files carry the Mexico ITRF2008 / LCC parameters without an EPSG code, so the
    CRS is declared explicitly as EPSG:6372.
    """
    layer = gpd.read_file(LAYER_DIR / f"{name}.shp")
    return layer.set_crs(config.CRS_METRIC, allow_override=True)


def clean() -> gpd.GeoDataFrame:
    ageb = read_layer("31a")
    ageb = ageb[ageb["CVE_MUN"] == config.MUNICIPALITY_CODE].copy()

    invalid = ~ageb.is_valid
    if invalid.any():
        ageb.loc[invalid, "geometry"] = ageb.loc[invalid, "geometry"].make_valid()
    if ageb["CVEGEO"].duplicated().any():
        raise ValueError("duplicate CVEGEO in the AGEB layer")

    localities = read_layer("31l")
    locality_names = localities.set_index("CVEGEO")["NOMGEO"].to_dict()
    municipalities = read_layer("31mun")
    municipality_names = municipalities.set_index("CVEGEO")["NOMGEO"].to_dict()

    ageb["area_km2"] = ageb.area / 1e6
    out = ageb.to_crs(config.CRS_STORAGE)
    out["geometry"] = out.geometry.apply(lambda g: g if g.geom_type == "MultiPolygon" else MultiPolygon([g]))

    out = out.rename(columns={
        "CVEGEO": "cvegeo", "CVE_ENT": "cve_ent", "CVE_MUN": "cve_mun",
        "CVE_LOC": "cve_loc", "CVE_AGEB": "cve_ageb",
    })
    out["municipality_name"] = (out["cve_ent"] + out["cve_mun"]).map(municipality_names)
    out["locality_name"] = (out["cve_ent"] + out["cve_mun"] + out["cve_loc"]).map(locality_names)
    out["geometries_repaired"] = invalid.values

    columns = ["cvegeo", "cve_ent", "cve_mun", "cve_loc", "cve_ageb", "municipality_name",
               "locality_name", "area_km2", "geometries_repaired", "geometry"]
    return out[columns].sort_values("cvegeo").reset_index(drop=True)


def municipality() -> gpd.GeoDataFrame:
    """The municipality polygon, the geography of the municipal crime counts."""
    mun = read_layer("31mun")
    mun = mun[mun["CVEGEO"] == config.STATE_MUN].copy()
    mun["area_km2"] = mun.area / 1e6
    mun = mun.to_crs(config.CRS_STORAGE)
    mun["geometry"] = mun.geometry.apply(lambda g: g if g.geom_type == "MultiPolygon" else MultiPolygon([g]))
    return mun.rename(columns={"CVEGEO": "cvegeo", "NOMGEO": "municipality_name"})[
        ["cvegeo", "municipality_name", "area_km2", "geometry"]].reset_index(drop=True)


def main() -> None:
    municipality().to_parquet(MUNICIPALITY_OUTPUT, index=False)
    frame = clean()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(OUTPUT, index=False)
    print(f"geography: {len(frame):,} urban AGEBs, {frame['area_km2'].sum():,.1f} km2, "
          f"{int(frame['geometries_repaired'].sum())} repaired -> {OUTPUT.relative_to(config.ROOT)}")


if __name__ == "__main__":
    main()
