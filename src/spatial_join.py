"""Assign establishments and crime incidents to urban AGEBs.

Rule:
1. A point is assigned to the AGEB polygon that contains it (`within`).
2. A point lying exactly on a polygon edge is not `within` any polygon; it is assigned to the
   touching polygon with the lowest CVEGEO, so the result is deterministic.
3. Any other point is unmatched and kept, with a reason, in unmatched_points.parquet.

Outputs (data/processed/): establishments_joined.parquet, crime_joined.parquet,
unmatched_points.parquet, and outputs/spatial_join_report.json.
"""

from __future__ import annotations

import json

import geopandas as gpd
import pandas as pd

from src import config

GEOGRAPHY = config.DATA_PROCESSED / "geography.parquet"
DENUE = config.DATA_PROCESSED / "denue.parquet"
CRIME = config.DATA_PROCESSED / "crime.parquet"

ESTABLISHMENTS_OUT = config.DATA_PROCESSED / "establishments_joined.parquet"
CRIME_OUT = config.DATA_PROCESSED / "crime_joined.parquet"
UNMATCHED_OUT = config.DATA_PROCESSED / "unmatched_points.parquet"
REPORT_OUT = config.OUTPUTS / "spatial_join_report.json"


def to_points(frame: pd.DataFrame) -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame(
        frame,
        geometry=gpd.points_from_xy(frame["longitude"], frame["latitude"]),
        crs=config.CRS_STORAGE,
    )


def assign(points: gpd.GeoDataFrame, polygons: gpd.GeoDataFrame, id_column: str):
    """Return (matched, unmatched): matched gains `cvegeo` and `join_method`."""
    areas = polygons[["cvegeo", "geometry"]]

    inside = gpd.sjoin(points, areas, how="inner", predicate="within")
    inside = inside.sort_values("cvegeo").drop_duplicates(id_column, keep="first")
    inside["join_method"] = "within"

    rest = points[~points[id_column].isin(inside[id_column])]
    edge = gpd.sjoin(rest, areas, how="inner", predicate="intersects")
    edge = edge.sort_values("cvegeo").drop_duplicates(id_column, keep="first")
    edge["join_method"] = "boundary"

    matched = pd.concat([inside, edge]).drop(columns="index_right")
    unmatched = points[~points[id_column].isin(matched[id_column])].copy()
    return gpd.GeoDataFrame(matched, geometry="geometry", crs=points.crs), unmatched


def main() -> None:
    polygons = gpd.read_parquet(GEOGRAPHY)
    urban_keys = set(polygons["cvegeo"])
    report = {}
    unmatched_frames = []

    # establishments
    denue = to_points(pd.read_parquet(DENUE))
    est, est_out = assign(denue, polygons, "denue_id")
    est["declared_matches_spatial"] = est["denue_cvegeo"] == est["cvegeo"]
    est.to_parquet(ESTABLISHMENTS_OUT, index=False)

    declared_urban = est_out["denue_cvegeo"].isin(urban_keys)
    est_out["reason"] = declared_urban.map({
        True: "declared in an urban AGEB but located outside every urban AGEB polygon",
        False: "declared outside the urban AGEBs (rural area)",
    })
    unmatched_frames.append(pd.DataFrame({
        "layer": "establishment", "point_id": est_out["denue_id"], "reason": est_out["reason"],
        "latitude": est_out["latitude"], "longitude": est_out["longitude"],
    }))
    report["establishments"] = {
        "points": len(denue),
        "assigned_within": int((est["join_method"] == "within").sum()),
        "assigned_boundary": int((est["join_method"] == "boundary").sum()),
        "unmatched": len(est_out),
        "unmatched_declared_rural": int((~declared_urban).sum()),
        "match_rate_pct": round(len(est) / len(denue) * 100, 2) if len(denue) else None,
        "declared_ageb_agreement_pct": round(est["declared_matches_spatial"].mean() * 100, 2),
    }

    # crime incidents
    crime = pd.read_parquet(CRIME)
    if len(crime):
        crime_pts = to_points(crime)
        inc, inc_out = assign(crime_pts, polygons, "source_incident_id")
        unmatched_frames.append(pd.DataFrame({
            "layer": "crime_incident", "point_id": inc_out["source_incident_id"],
            "reason": "located outside every urban AGEB polygon",
            "latitude": inc_out["latitude"], "longitude": inc_out["longitude"],
        }))
        report["crime_incidents"] = {
            "points": len(crime_pts),
            "assigned_within": int((inc["join_method"] == "within").sum()),
            "assigned_boundary": int((inc["join_method"] == "boundary").sum()),
            "unmatched": len(inc_out),
            "match_rate_pct": round(len(inc) / len(crime_pts) * 100, 2),
        }
    else:
        inc = gpd.GeoDataFrame(crime.assign(cvegeo=pd.Series(dtype=str), join_method=pd.Series(dtype=str)),
                               geometry=gpd.points_from_xy([], []), crs=config.CRS_STORAGE)
        report["crime_incidents"] = {"points": 0, "note": "crime source not available"}
    inc.to_parquet(CRIME_OUT, index=False)

    pd.concat(unmatched_frames, ignore_index=True).to_parquet(UNMATCHED_OUT, index=False)
    REPORT_OUT.parent.mkdir(parents=True, exist_ok=True)
    REPORT_OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"spatial join: {json.dumps(report)}")


if __name__ == "__main__":
    main()
