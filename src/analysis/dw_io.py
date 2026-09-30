"""The only data access used by the analysis: read views from the warehouse."""

from __future__ import annotations

import geopandas as gpd
import pandas as pd
from sqlalchemy import create_engine, text

from src import config

_ENGINE = None


def engine():
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = create_engine(config.database_url())
    return _ENGINE


def read_from_dw(view: str, geometry: bool = False) -> pd.DataFrame | gpd.GeoDataFrame:
    """Read a dw view or table. With geometry=True the `geom` column is returned as a
    GeoDataFrame projected to the metric CRS used for maps and spatial weights."""
    if not view.replace("_", "").isalnum():
        raise ValueError(f"invalid view name: {view}")
    sql = f"SELECT * FROM dw.{view}"
    if geometry:
        frame = gpd.read_postgis(sql, engine(), geom_col="geom")
        return frame.to_crs(config.CRS_METRIC)
    with engine().connect() as conn:
        return pd.read_sql(text(sql), conn)


def crime_loaded() -> bool:
    with engine().connect() as conn:
        return bool(conn.execute(text(
            "SELECT EXISTS (SELECT 1 FROM dw.dim_source WHERE layer = 'public_safety')")).scalar())
