"""Project configuration: paths, geographic constants and database connection."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

# --- paths -----------------------------------------------------------------
DATA_RAW = ROOT / "data" / "raw"
DATA_PROCESSED = ROOT / "data" / "processed"
DOCS = ROOT / "docs"
OUTPUTS = ROOT / "outputs"
MAPS = OUTPUTS / "maps"
FIGURES = OUTPUTS / "figures"
SQL = ROOT / "sql"
SOURCE_MANIFEST = DOCS / "source_manifest.json"

# --- study area ------------------------------------------------------------
STATE_CODE = "31"          # Yucatán
MUNICIPALITY_CODE = "050"  # Mérida
STATE_MUN = STATE_CODE + MUNICIPALITY_CODE

# --- coordinate reference systems ------------------------------------------
CRS_STORAGE = "EPSG:4326"  # WGS84, used for stored geometries and source points
CRS_METRIC = "EPSG:6372"   # Mexico ITRF2008 / LCC, metres, used for areas
SRID_STORAGE = 4326

# --- sources ---------------------------------------------------------------
SOURCES = {
    "census": {
        "name": "INEGI Censo de Población y Vivienda 2020 - AGEB y manzana urbana",
        "provider": "INEGI",
        "edition": "2020",
        "url": (
            "https://www.inegi.org.mx/contenidos/programas/ccpv/2020/datosabiertos/"
            "ageb_manzana/ageb_mza_urbana_31_cpv2020_csv.zip"
        ),
        "original_grain": "one row per urban block, with total rows per AGEB, locality, "
                          "municipality and state",
    },
    "geography": {
        "name": "INEGI Marco Geoestadístico - Censo de Población y Vivienda 2020",
        "provider": "INEGI",
        "edition": "2020",
        "url": (
            "https://www.inegi.org.mx/contenidos/productos/prod_serv/contenidos/espanol/"
            "bvinegi/productos/geografia/marcogeo/889463807469/31_yucatan.zip"
        ),
        "original_grain": "one polygon per geostatistical area (state, municipality, "
                          "locality, AGEB, block)",
    },
    "denue": {
        "name": "INEGI Directorio Estadístico Nacional de Unidades Económicas",
        "provider": "INEGI",
        "edition": "latest published (see download date)",
        "url": "https://www.inegi.org.mx/contenidos/masiva/denue/denue_31_csv.zip",
        "original_grain": "one row per establishment",
    },
}


def database_url() -> str:
    """SQLAlchemy URL built from environment variables."""
    user = os.environ.get("PGUSER", "postgres")
    password = os.environ.get("PGPASSWORD", "")
    host = os.environ.get("PGHOST", "localhost")
    port = os.environ.get("PGPORT", "5432")
    name = os.environ.get("PGDATABASE", "merida_dw")
    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{name}"
