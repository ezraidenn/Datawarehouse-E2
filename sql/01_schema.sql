-- =============================================================================
-- 01_schema.sql — Mérida Urban Intelligence Data Warehouse
-- Creates the staging and dw schemas and the dimensional model.
-- Idempotent: both schemas are dropped and rebuilt on every run.
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS postgis;

DROP SCHEMA IF EXISTS dw CASCADE;
DROP SCHEMA IF EXISTS staging CASCADE;
CREATE SCHEMA staging;
CREATE SCHEMA dw;

COMMENT ON SCHEMA staging IS 'Cleaned and spatially joined tables as loaded by the Python ETL.';
COMMENT ON SCHEMA dw IS 'Dimensional model (constellation schema) and KPI views.';

-- -----------------------------------------------------------------------------
-- Dimensions
-- -----------------------------------------------------------------------------

CREATE TABLE dw.dim_source (
    source_key      integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source_code     text NOT NULL UNIQUE,
    layer           text NOT NULL CHECK (layer IN ('demographic', 'economic', 'geographic', 'public_safety')),
    source_name     text NOT NULL,
    provider        text NOT NULL,
    edition         text,
    url             text,
    download_date   date,
    original_grain  text,
    file_name       text,
    sha256          char(64)
);
COMMENT ON TABLE dw.dim_source IS 'Grain: one row per original dataset. Provenance of every fact row.';
COMMENT ON COLUMN dw.dim_source.source_code IS 'Short code of the dataset (census, geography, denue, crime).';
COMMENT ON COLUMN dw.dim_source.layer IS 'Thematic layer the dataset belongs to.';
COMMENT ON COLUMN dw.dim_source.sha256 IS 'Checksum of the raw file as downloaded.';

CREATE TABLE dw.dim_geography (
    geography_key     integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    cvegeo            char(13) NOT NULL UNIQUE,
    cve_ent           char(2) NOT NULL,
    cve_mun           char(3) NOT NULL,
    cve_loc           char(4) NOT NULL,
    cve_ageb          char(4) NOT NULL,
    municipality_name text,
    locality_name     text,
    area_km2          numeric(12, 6) NOT NULL CHECK (area_km2 > 0),
    geom              geometry(MultiPolygon, 4326) NOT NULL,
    centroid          geometry(Point, 4326) NOT NULL,
    source_key        integer NOT NULL REFERENCES dw.dim_source (source_key)
);
CREATE INDEX dim_geography_geom_gix ON dw.dim_geography USING gist (geom);
COMMENT ON TABLE dw.dim_geography IS 'Grain: one row per urban AGEB of the municipality of Mérida (Marco Geoestadístico 2020). Conformed dimension shared by all facts.';
COMMENT ON COLUMN dw.dim_geography.cvegeo IS 'INEGI geostatistical key: state (2) + municipality (3) + locality (4) + AGEB (4).';
COMMENT ON COLUMN dw.dim_geography.area_km2 IS 'Polygon area in square kilometres, measured in EPSG:6372.';
COMMENT ON COLUMN dw.dim_geography.geom IS 'AGEB polygon in WGS84 (EPSG:4326).';
COMMENT ON COLUMN dw.dim_geography.centroid IS 'Point guaranteed to lie inside the polygon, for labels.';

CREATE TABLE dw.dim_municipality (
    municipality_key  integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    cvegeo            char(5) NOT NULL UNIQUE,
    municipality_name text NOT NULL,
    area_km2          numeric(12, 4) NOT NULL CHECK (area_km2 > 0),
    pop_total_2020    integer NOT NULL,
    geom              geometry(MultiPolygon, 4326) NOT NULL,
    source_key        integer NOT NULL REFERENCES dw.dim_source (source_key)
);
COMMENT ON TABLE dw.dim_municipality IS 'Grain: one row per municipality (Mérida). Geography of the municipal crime counts, which have no location inside the city.';
COMMENT ON COLUMN dw.dim_municipality.cvegeo IS 'INEGI municipal key: state (2) + municipality (3).';
COMMENT ON COLUMN dw.dim_municipality.municipality_name IS 'Municipality name (Marco Geoestadístico).';
COMMENT ON COLUMN dw.dim_municipality.area_km2 IS 'Municipal area in square kilometres, measured in EPSG:6372.';
COMMENT ON COLUMN dw.dim_municipality.pop_total_2020 IS 'Total population of the municipality, Census 2020 municipal total row; denominator of municipal crime rates.';
COMMENT ON COLUMN dw.dim_municipality.geom IS 'Municipal polygon in WGS84 (EPSG:4326).';

CREATE TABLE dw.dim_activity (
    activity_key  integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    scian_code    char(6) NOT NULL UNIQUE,
    activity_name text NOT NULL,
    sector_code   char(2) NOT NULL,
    sector_name   text NOT NULL,
    sector_group  text NOT NULL CHECK (sector_group IN ('retail', 'service', 'other'))
);
COMMENT ON TABLE dw.dim_activity IS 'Grain: one row per SCIAN activity class present in DENUE for Mérida.';
COMMENT ON COLUMN dw.dim_activity.sector_name IS 'Sector name; sectors split across several codes (31-33, 48-49) share one name.';
COMMENT ON COLUMN dw.dim_activity.sector_group IS 'retail = SCIAN 46; service = SCIAN 51 to 81; other = everything else.';

CREATE TABLE dw.dim_business_size (
    size_key      integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    size_label    text NOT NULL UNIQUE,
    size_order    smallint NOT NULL UNIQUE,
    min_employees integer NOT NULL,
    max_employees integer
);
COMMENT ON TABLE dw.dim_business_size IS 'Grain: one row per DENUE employment stratum (per_ocu).';
COMMENT ON COLUMN dw.dim_business_size.max_employees IS 'Upper bound of the stratum; NULL for the open top stratum.';

CREATE TABLE dw.dim_crime_type (
    crime_type_key integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    crime_type     text NOT NULL UNIQUE,
    crime_category text,
    crime_group    text NOT NULL
);
COMMENT ON COLUMN dw.dim_crime_type.crime_category IS 'Broader crime type of the source (SESNSP "tipo de delito"), when published.';
COMMENT ON TABLE dw.dim_crime_type IS 'Grain: one row per crime category published by the incident source.';
COMMENT ON COLUMN dw.dim_crime_type.crime_group IS 'Harmonised group of the category.';

CREATE TABLE dw.dim_date (
    date_key     integer PRIMARY KEY,
    full_date    date,
    year         smallint,
    quarter      smallint,
    month        smallint,
    month_name   text,
    day          smallint,
    day_of_week  smallint,
    day_name     text,
    is_weekend   boolean
);
COMMENT ON TABLE dw.dim_date IS 'Grain: one row per calendar day of the incident period; key yyyymmdd, 0 = unknown date.';

CREATE TABLE dw.dim_time_of_day (
    time_key  smallint PRIMARY KEY,
    hour      smallint,
    day_part  text NOT NULL
);
COMMENT ON TABLE dw.dim_time_of_day IS 'Grain: one row per hour of the day (0-23); -1 = unknown time.';
COMMENT ON COLUMN dw.dim_time_of_day.day_part IS 'early morning 0-5, morning 6-11, afternoon 12-18, night 19-23.';

-- -----------------------------------------------------------------------------
-- Facts
-- -----------------------------------------------------------------------------

CREATE TABLE dw.fact_demographics (
    geography_key       integer PRIMARY KEY REFERENCES dw.dim_geography (geography_key),
    source_key          integer NOT NULL REFERENCES dw.dim_source (source_key),
    pop_total           integer,
    pop_0_14            integer,
    pop_15_64           integer,
    pop_65_plus         integer,
    pop_12_plus         integer,
    pop_econ_active     integer,
    pop_employed        integer,
    dwellings_total     integer,
    dwellings_inhabited integer,
    avg_occupants       numeric(6, 2),
    has_suppressed      boolean NOT NULL
);
COMMENT ON TABLE dw.fact_demographics IS 'Grain: one row per urban AGEB, Census 2020 (AGEB total rows published by INEGI).';
COMMENT ON COLUMN dw.fact_demographics.pop_total IS 'Total population (POBTOT).';
COMMENT ON COLUMN dw.fact_demographics.pop_0_14 IS 'Population aged 0 to 14 (POB0_14).';
COMMENT ON COLUMN dw.fact_demographics.pop_15_64 IS 'Population aged 15 to 64 (POB15_64).';
COMMENT ON COLUMN dw.fact_demographics.pop_65_plus IS 'Population aged 65 and over (POB65_MAS).';
COMMENT ON COLUMN dw.fact_demographics.pop_12_plus IS 'Population aged 12 and over (P_12YMAS), base of the activity rate.';
COMMENT ON COLUMN dw.fact_demographics.pop_econ_active IS 'Economically active population (PEA).';
COMMENT ON COLUMN dw.fact_demographics.pop_employed IS 'Employed population (POCUPADA).';
COMMENT ON COLUMN dw.fact_demographics.dwellings_total IS 'Total dwellings (VIVTOT).';
COMMENT ON COLUMN dw.fact_demographics.dwellings_inhabited IS 'Inhabited dwellings (TVIVHAB).';
COMMENT ON COLUMN dw.fact_demographics.avg_occupants IS 'Average occupants per inhabited private dwelling (PROM_OCUP).';
COMMENT ON COLUMN dw.fact_demographics.has_suppressed IS 'True when INEGI withheld at least one value for confidentiality; withheld values are NULL, never zero.';

CREATE TABLE dw.fact_establishment (
    establishment_key  integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    denue_id           text NOT NULL UNIQUE,
    geography_key      integer NOT NULL REFERENCES dw.dim_geography (geography_key),
    activity_key       integer NOT NULL REFERENCES dw.dim_activity (activity_key),
    size_key           integer NOT NULL REFERENCES dw.dim_business_size (size_key),
    source_key         integer NOT NULL REFERENCES dw.dim_source (source_key),
    establishment_name text,
    denue_cvegeo       char(13),
    join_method        text NOT NULL CHECK (join_method IN ('within', 'boundary')),
    geom               geometry(Point, 4326) NOT NULL,
    establishment_count smallint NOT NULL DEFAULT 1
);
CREATE INDEX fact_establishment_geography_idx ON dw.fact_establishment (geography_key);
CREATE INDEX fact_establishment_activity_idx ON dw.fact_establishment (activity_key);
CREATE INDEX fact_establishment_geom_gix ON dw.fact_establishment USING gist (geom);
COMMENT ON TABLE dw.fact_establishment IS 'Grain: one row per DENUE establishment located inside an urban AGEB of Mérida.';
COMMENT ON COLUMN dw.fact_establishment.denue_cvegeo IS 'AGEB key declared by DENUE, kept to audit the spatial join.';
COMMENT ON COLUMN dw.fact_establishment.join_method IS 'within = point inside the polygon; boundary = point on a polygon edge.';
COMMENT ON COLUMN dw.fact_establishment.establishment_count IS 'Additive measure, always 1.';

CREATE TABLE dw.fact_crime_incident (
    incident_key       integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source_incident_id text NOT NULL UNIQUE,
    geography_key      integer NOT NULL REFERENCES dw.dim_geography (geography_key),
    crime_type_key     integer NOT NULL REFERENCES dw.dim_crime_type (crime_type_key),
    date_key           integer NOT NULL REFERENCES dw.dim_date (date_key),
    time_key           smallint NOT NULL REFERENCES dw.dim_time_of_day (time_key),
    source_key         integer NOT NULL REFERENCES dw.dim_source (source_key),
    location_precision text NOT NULL,
    join_method        text NOT NULL CHECK (join_method IN ('within', 'boundary')),
    geom               geometry(Point, 4326) NOT NULL,
    incident_count     smallint NOT NULL DEFAULT 1
);
CREATE INDEX fact_crime_geography_idx ON dw.fact_crime_incident (geography_key);

CREATE TABLE dw.fact_crime_municipal (
    crime_municipal_key integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    municipality_key    integer NOT NULL REFERENCES dw.dim_municipality (municipality_key),
    crime_type_key      integer NOT NULL REFERENCES dw.dim_crime_type (crime_type_key),
    date_key            integer NOT NULL REFERENCES dw.dim_date (date_key),
    source_key          integer NOT NULL REFERENCES dw.dim_source (source_key),
    modality            text NOT NULL,
    incidents           integer NOT NULL CHECK (incidents >= 0),
    UNIQUE (municipality_key, crime_type_key, modality, date_key)
);
COMMENT ON TABLE dw.fact_crime_municipal IS 'Grain: one municipality x month x crime modality (SESNSP). Incidents without location: they describe the municipality as a whole and are never assigned to AGEBs.';
COMMENT ON COLUMN dw.fact_crime_municipal.date_key IS 'First day of the month (yyyymm01).';
COMMENT ON COLUMN dw.fact_crime_municipal.modality IS 'Crime modality as published (SESNSP "modalidad").';
COMMENT ON COLUMN dw.fact_crime_municipal.incidents IS 'Number of incidents reported in the month (additive).';
CREATE INDEX fact_crime_geom_gix ON dw.fact_crime_incident USING gist (geom);
COMMENT ON TABLE dw.fact_crime_incident IS 'Grain: one row per georeferenced crime incident located inside an urban AGEB of Mérida.';
COMMENT ON COLUMN dw.fact_crime_incident.location_precision IS 'point, centroid or approximate, as declared for the source.';
COMMENT ON COLUMN dw.fact_crime_incident.incident_count IS 'Additive measure, always 1.';

-- Descriptive columns without an obvious meaning ----------------------------------
COMMENT ON COLUMN dw.dim_geography.cve_ent IS 'State code (31 = Yucatán).';
COMMENT ON COLUMN dw.dim_geography.cve_mun IS 'Municipality code (050 = Mérida).';
COMMENT ON COLUMN dw.dim_geography.cve_loc IS 'Locality code within the municipality.';
COMMENT ON COLUMN dw.dim_geography.cve_ageb IS 'AGEB code within the locality.';
COMMENT ON COLUMN dw.dim_activity.scian_code IS 'Six-digit SCIAN activity class (DENUE codigo_act).';
COMMENT ON COLUMN dw.dim_activity.sector_code IS 'Two-digit SCIAN sector.';
COMMENT ON COLUMN dw.fact_establishment.denue_id IS 'Establishment identifier in DENUE (id).';
COMMENT ON COLUMN dw.fact_establishment.establishment_name IS 'Establishment name as published (nom_estab).';
COMMENT ON COLUMN dw.fact_establishment.geom IS 'Establishment location in WGS84, from DENUE latitude/longitude.';
COMMENT ON COLUMN dw.fact_crime_incident.source_incident_id IS 'Incident identifier in the source, or a hash of the raw row when the source has none.';
COMMENT ON COLUMN dw.fact_crime_incident.geom IS 'Incident location in WGS84, from the source latitude/longitude.';
COMMENT ON COLUMN dw.fact_crime_incident.join_method IS 'within = point inside the polygon; boundary = point on a polygon edge.';
COMMENT ON COLUMN dw.dim_geography.municipality_name IS 'Municipality name (Marco Geoestadístico).';
COMMENT ON COLUMN dw.dim_geography.locality_name IS 'Locality name (Marco Geoestadístico).';
COMMENT ON COLUMN dw.dim_activity.activity_name IS 'SCIAN activity class name (DENUE nombre_act).';
COMMENT ON COLUMN dw.dim_business_size.size_label IS 'Employment stratum as published by DENUE (per_ocu).';
COMMENT ON COLUMN dw.dim_business_size.size_order IS 'Order of the stratum from smallest (1) to largest (7).';
COMMENT ON COLUMN dw.dim_business_size.min_employees IS 'Lower bound of the stratum.';
COMMENT ON COLUMN dw.dim_crime_type.crime_type IS 'Crime category as published by the source, upper case.';
COMMENT ON COLUMN dw.dim_date.full_date IS 'Calendar date; NULL for the unknown member.';
COMMENT ON COLUMN dw.dim_date.year IS 'Calendar year.';
COMMENT ON COLUMN dw.dim_date.quarter IS 'Quarter 1-4.';
COMMENT ON COLUMN dw.dim_date.month IS 'Month 1-12.';
COMMENT ON COLUMN dw.dim_date.month_name IS 'Month name.';
COMMENT ON COLUMN dw.dim_date.day IS 'Day of the month.';
COMMENT ON COLUMN dw.dim_date.day_of_week IS 'ISO day of week, 1 = Monday.';
COMMENT ON COLUMN dw.dim_date.day_name IS 'Day name.';
COMMENT ON COLUMN dw.dim_date.is_weekend IS 'True on Saturday and Sunday.';
COMMENT ON COLUMN dw.dim_time_of_day.hour IS 'Hour of the day 0-23; NULL for the unknown member.';
COMMENT ON COLUMN dw.dim_source.source_name IS 'Dataset name.';
COMMENT ON COLUMN dw.dim_source.provider IS 'Publishing institution.';
COMMENT ON COLUMN dw.dim_source.edition IS 'Edition or reference year.';
COMMENT ON COLUMN dw.dim_source.url IS 'Download URL.';
COMMENT ON COLUMN dw.dim_source.download_date IS 'Date the raw file was downloaded.';
COMMENT ON COLUMN dw.dim_source.original_grain IS 'Grain of the dataset as published.';
COMMENT ON COLUMN dw.dim_source.file_name IS 'Raw file name under data/raw.';
