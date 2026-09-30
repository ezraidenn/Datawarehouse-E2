# Mérida Urban Intelligence — Geospatial Data Warehouse

A reproducible geospatial Data Warehouse that integrates demographic, economic, geographic and
public-safety data for the city of Mérida, Yucatán, to calculate territorial KPIs, compare areas
and explore whether their patterns are geographically associated.

> Work in progress. Sections are completed as each project phase is finished.

## 1. Project overview and analytical objective

_Pending._

## 2. Data sources

_Pending: source, edition, original grain and relevant variables._

## 3. Geographic strategy

_Pending: alternatives considered, selected unit, latitude/longitude-to-polygon integration._

## 4. ETL pipeline

_Pending: cleaning, transformation and spatial-integration decisions._

## 5. Database setup and Data Warehouse model

See [docs/database_setup.md](docs/database_setup.md).

_Pending: facts, dimensions, grain and relationships._

## 6. KPI definitions and formulas

_Pending._

## 7. Repository structure

```text
├── data/raw/          original downloads, never edited (not versioned)
├── data/processed/    cleaned intermediates (not versioned)
├── notebooks/         assessment and analysis notebooks
├── src/               download, cleaning, spatial join, load and analysis code
├── sql/               schema, load, views and validation scripts
├── docs/              data dictionary, model diagram, decisions and report
└── outputs/           generated maps and figures
```

## 8. How to reproduce

```bash
python -m venv .venv
source .venv/Scripts/activate        # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                 # set the database credentials
docker compose up -d                 # PostgreSQL 17 + PostGIS (see docs/database_setup.md)
python -m src.download               # fetch the original sources into data/raw
```

_Pending: pipeline and analysis commands._

## 9. Assumptions, data-quality issues and limitations

_Pending._
