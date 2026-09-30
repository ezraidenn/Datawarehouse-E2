# Data dictionary

Schema `dw` of the `merida_dw` database. Generated from the database catalog by
`python -m src.make_data_dictionary`; descriptions are the `COMMENT ON` texts of
`sql/01_schema.sql` and `sql/03_views.sql`. The grain of each table is stated in its
description.

## Contents

| Object | Type | Rows | Description |
|---|---|---|---|
| [`dim_activity`](#dimactivity) | table | 744 | Grain: one row per SCIAN activity class present in DENUE for Mérida. |
| [`dim_business_size`](#dimbusinesssize) | table | 7 | Grain: one row per DENUE employment stratum (per_ocu). |
| [`dim_crime_type`](#dimcrimetype) | table | 0 | Grain: one row per crime category published by the incident source. |
| [`dim_date`](#dimdate) | table | 1 | Grain: one row per calendar day of the incident period; key yyyymmdd, 0 = unknown date. |
| [`dim_geography`](#dimgeography) | table | 526 | Grain: one row per urban AGEB of the municipality of Mérida (Marco Geoestadístico 2020). Conformed dimension shared by all facts. |
| [`dim_source`](#dimsource) | table | 3 | Grain: one row per original dataset. Provenance of every fact row. |
| [`dim_time_of_day`](#dimtimeofday) | table | 25 | Grain: one row per hour of the day (0-23); -1 = unknown time. |
| [`fact_crime_incident`](#factcrimeincident) | table | 0 | Grain: one row per georeferenced crime incident located inside an urban AGEB of Mérida. |
| [`fact_demographics`](#factdemographics) | table | 526 | Grain: one row per urban AGEB, Census 2020 (AGEB total rows published by INEGI). |
| [`fact_establishment`](#factestablishment) | table | 56,664 | Grain: one row per DENUE establishment located inside an urban AGEB of Mérida. |
| [`vw_activity_by_ageb`](#vwactivitybyageb) | view | 5,396 | Grain: AGEB x SCIAN sector (by name). Establishment counts and rank within the AGEB; ties broken by sector code. |
| [`vw_crime_by_type_time`](#vwcrimebytypetime) | view | 0 | Grain: AGEB x crime type x year x month x weekday x part of day. Incident counts. |
| [`vw_kpi_ageb`](#vwkpiageb) | view | 526 | Grain: one row per urban AGEB. The scalar KPIs of the project; KPI 13 (incidents by type and time) is dw.vw_crime_by_type_time. |
| [`vw_kpi_ageb_geo`](#vwkpiagebgeo) | view | 526 | Grain: one row per urban AGEB. vw_kpi_ageb plus the AGEB polygon. |
| [`vw_kpi_city`](#vwkpicity) | view | 1 | Grain: one row for the whole study area. Totals and city-wide ratios. |
| [`vw_population_by_age`](#vwpopulationbyage) | view | 1,578 | Grain: AGEB x age group. Population counts and shares of the AGEB total. |

## dim_activity

*table* — Grain: one row per SCIAN activity class present in DENUE for Mérida.

| Column | Type | Key | Null | Description |
|---|---|---|---|---|
| `activity_key` | integer | PK | no | Surrogate key. |
| `scian_code` | character(6) |  | no | Six-digit SCIAN activity class (DENUE codigo_act). |
| `activity_name` | text |  | no | SCIAN activity class name (DENUE nombre_act). |
| `sector_code` | character(2) |  | no | Two-digit SCIAN sector. |
| `sector_name` | text |  | no | Sector name; sectors split across several codes (31-33, 48-49) share one name. |
| `sector_group` | text |  | no | retail = SCIAN 46; service = SCIAN 51 to 81; other = everything else. |

## dim_business_size

*table* — Grain: one row per DENUE employment stratum (per_ocu).

| Column | Type | Key | Null | Description |
|---|---|---|---|---|
| `size_key` | integer | PK | no | Surrogate key. |
| `size_label` | text |  | no | Employment stratum as published by DENUE (per_ocu). |
| `size_order` | smallint |  | no | Order of the stratum from smallest (1) to largest (7). |
| `min_employees` | integer |  | no | Lower bound of the stratum. |
| `max_employees` | integer |  | yes | Upper bound of the stratum; NULL for the open top stratum. |

## dim_crime_type

*table* — Grain: one row per crime category published by the incident source.

| Column | Type | Key | Null | Description |
|---|---|---|---|---|
| `crime_type_key` | integer | PK | no | Surrogate key. |
| `crime_type` | text |  | no | Crime category as published by the source, upper case. |
| `crime_group` | text |  | no | Harmonised group of the category. |

## dim_date

*table* — Grain: one row per calendar day of the incident period; key yyyymmdd, 0 = unknown date.

| Column | Type | Key | Null | Description |
|---|---|---|---|---|
| `date_key` | integer | PK | no | Surrogate key. |
| `full_date` | date |  | yes | Calendar date; NULL for the unknown member. |
| `year` | smallint |  | yes | Calendar year. |
| `quarter` | smallint |  | yes | Quarter 1-4. |
| `month` | smallint |  | yes | Month 1-12. |
| `month_name` | text |  | yes | Month name. |
| `day` | smallint |  | yes | Day of the month. |
| `day_of_week` | smallint |  | yes | ISO day of week, 1 = Monday. |
| `day_name` | text |  | yes | Day name. |
| `is_weekend` | boolean |  | yes | True on Saturday and Sunday. |

## dim_geography

*table* — Grain: one row per urban AGEB of the municipality of Mérida (Marco Geoestadístico 2020). Conformed dimension shared by all facts.

| Column | Type | Key | Null | Description |
|---|---|---|---|---|
| `geography_key` | integer | PK | no | Surrogate key. |
| `cvegeo` | character(13) |  | no | INEGI geostatistical key: state (2) + municipality (3) + locality (4) + AGEB (4). |
| `cve_ent` | character(2) |  | no | State code (31 = Yucatán). |
| `cve_mun` | character(3) |  | no | Municipality code (050 = Mérida). |
| `cve_loc` | character(4) |  | no | Locality code within the municipality. |
| `cve_ageb` | character(4) |  | no | AGEB code within the locality. |
| `municipality_name` | text |  | yes | Municipality name (Marco Geoestadístico). |
| `locality_name` | text |  | yes | Locality name (Marco Geoestadístico). |
| `area_km2` | numeric(12,6) |  | no | Polygon area in square kilometres, measured in EPSG:6372. |
| `geom` | geometry(MultiPolygon,4326) |  | no | AGEB polygon in WGS84 (EPSG:4326). |
| `centroid` | geometry(Point,4326) |  | no | Point guaranteed to lie inside the polygon, for labels. |
| `source_key` | integer | FK → dim_source | no | Reference to dim_source. |

## dim_source

*table* — Grain: one row per original dataset. Provenance of every fact row.

| Column | Type | Key | Null | Description |
|---|---|---|---|---|
| `source_key` | integer | PK | no | Surrogate key. |
| `source_code` | text |  | no | Short code of the dataset (census, geography, denue, crime). |
| `layer` | text |  | no | Thematic layer the dataset belongs to. |
| `source_name` | text |  | no | Dataset name. |
| `provider` | text |  | no | Publishing institution. |
| `edition` | text |  | yes | Edition or reference year. |
| `url` | text |  | yes | Download URL. |
| `download_date` | date |  | yes | Date the raw file was downloaded. |
| `original_grain` | text |  | yes | Grain of the dataset as published. |
| `file_name` | text |  | yes | Raw file name under data/raw. |
| `sha256` | character(64) |  | yes | Checksum of the raw file as downloaded. |

## dim_time_of_day

*table* — Grain: one row per hour of the day (0-23); -1 = unknown time.

| Column | Type | Key | Null | Description |
|---|---|---|---|---|
| `time_key` | smallint | PK | no | Surrogate key. |
| `hour` | smallint |  | yes | Hour of the day 0-23; NULL for the unknown member. |
| `day_part` | text |  | no | early morning 0-5, morning 6-11, afternoon 12-18, night 19-23. |

## fact_crime_incident

*table* — Grain: one row per georeferenced crime incident located inside an urban AGEB of Mérida.

| Column | Type | Key | Null | Description |
|---|---|---|---|---|
| `incident_key` | integer | PK | no | Surrogate key. |
| `source_incident_id` | text |  | no | Incident identifier in the source, or a hash of the raw row when the source has none. |
| `geography_key` | integer | FK → dim_geography | no | Reference to dim_geography. |
| `crime_type_key` | integer | FK → dim_crime_type | no | Reference to dim_crime_type. |
| `date_key` | integer | FK → dim_date | no | Reference to dim_date. |
| `time_key` | smallint | FK → dim_time_of_day | no | Reference to dim_time_of_day. |
| `source_key` | integer | FK → dim_source | no | Reference to dim_source. |
| `location_precision` | text |  | no | point, centroid or approximate, as declared for the source. |
| `join_method` | text |  | no | within = point inside the polygon; boundary = point on a polygon edge. |
| `geom` | geometry(Point,4326) |  | no | Incident location in WGS84, from the source latitude/longitude. |
| `incident_count` | smallint |  | no | Additive measure, always 1. |

## fact_demographics

*table* — Grain: one row per urban AGEB, Census 2020 (AGEB total rows published by INEGI).

| Column | Type | Key | Null | Description |
|---|---|---|---|---|
| `geography_key` | integer | PK | no | Surrogate key. |
| `source_key` | integer | FK → dim_source | no | Reference to dim_source. |
| `pop_total` | integer |  | yes | Total population (POBTOT). |
| `pop_0_14` | integer |  | yes | Population aged 0 to 14 (POB0_14). |
| `pop_15_64` | integer |  | yes | Population aged 15 to 64 (POB15_64). |
| `pop_65_plus` | integer |  | yes | Population aged 65 and over (POB65_MAS). |
| `pop_12_plus` | integer |  | yes | Population aged 12 and over (P_12YMAS), base of the activity rate. |
| `pop_econ_active` | integer |  | yes | Economically active population (PEA). |
| `pop_employed` | integer |  | yes | Employed population (POCUPADA). |
| `dwellings_total` | integer |  | yes | Total dwellings (VIVTOT). |
| `dwellings_inhabited` | integer |  | yes | Inhabited dwellings (TVIVHAB). |
| `avg_occupants` | numeric(6,2) |  | yes | Average occupants per inhabited private dwelling (PROM_OCUP). |
| `has_suppressed` | boolean |  | no | True when INEGI withheld at least one value for confidentiality; withheld values are NULL, never zero. |

## fact_establishment

*table* — Grain: one row per DENUE establishment located inside an urban AGEB of Mérida.

| Column | Type | Key | Null | Description |
|---|---|---|---|---|
| `establishment_key` | integer | PK | no | Surrogate key. |
| `denue_id` | text |  | no | Establishment identifier in DENUE (id). |
| `geography_key` | integer | FK → dim_geography | no | Reference to dim_geography. |
| `activity_key` | integer | FK → dim_activity | no | Reference to dim_activity. |
| `size_key` | integer | FK → dim_business_size | no | Reference to dim_business_size. |
| `source_key` | integer | FK → dim_source | no | Reference to dim_source. |
| `establishment_name` | text |  | yes | Establishment name as published (nom_estab). |
| `denue_cvegeo` | character(13) |  | yes | AGEB key declared by DENUE, kept to audit the spatial join. |
| `join_method` | text |  | no | within = point inside the polygon; boundary = point on a polygon edge. |
| `geom` | geometry(Point,4326) |  | no | Establishment location in WGS84, from DENUE latitude/longitude. |
| `establishment_count` | smallint |  | no | Additive measure, always 1. |

## vw_activity_by_ageb

*view* — Grain: AGEB x SCIAN sector (by name). Establishment counts and rank within the AGEB; ties broken by sector code.

| Column | Type | Key | Null | Description |
|---|---|---|---|---|
| `cvegeo` | character(13) |  |  | AGEB key. |
| `sector_name` | text |  |  | Sector name; sectors split across several codes (31-33, 48-49) share one name. |
| `first_sector_code` | bpchar |  |  | Lowest SCIAN code of the sector (31 for manufacturing). |
| `sector_group` | text |  |  | retail = SCIAN 46; service = SCIAN 51 to 81; other = everything else. |
| `establishments` | bigint |  |  | Number of establishments of the sector in the AGEB. |
| `rank_in_ageb` | bigint |  |  | Rank of the sector within the AGEB by establishments, 1 = dominant. |

## vw_crime_by_type_time

*view* — Grain: AGEB x crime type x year x month x weekday x part of day. Incident counts.

| Column | Type | Key | Null | Description |
|---|---|---|---|---|
| `cvegeo` | character(13) |  |  | AGEB key. |
| `crime_type` | text |  |  | Crime category as published by the source, upper case. |
| `crime_group` | text |  |  | Harmonised group of the category. |
| `year` | smallint |  |  | Calendar year. |
| `month` | smallint |  |  | Month 1-12. |
| `month_name` | text |  |  | Month name. |
| `day_name` | text |  |  | Day name. |
| `is_weekend` | boolean |  |  | True on Saturday and Sunday. |
| `day_part` | text |  |  | Part of the day of the incident. |
| `incidents` | bigint |  |  | Number of incidents. |

## vw_kpi_ageb

*view* — Grain: one row per urban AGEB. The scalar KPIs of the project; KPI 13 (incidents by type and time) is dw.vw_crime_by_type_time.

| Column | Type | Key | Null | Description |
|---|---|---|---|---|
| `cvegeo` | character(13) |  |  | AGEB key. |
| `locality_name` | text |  |  | Locality the AGEB belongs to. |
| `area_km2` | numeric |  |  | AGEB area, km². |
| `pop_total` | integer |  |  | KPI 1 Total population. |
| `pop_density_km2` | numeric |  |  | KPI 2 Population density: pop_total / area_km2. |
| `pea_rate_pct` | numeric |  |  | KPI 3 Economically active population rate: 100 x PEA / population aged 12+. |
| `share_0_14_pct` | numeric |  |  | KPI 4 Share of population aged 0-14, %. |
| `share_15_64_pct` | numeric |  |  | KPI 4 Share of population aged 15-64, %. |
| `share_65_plus_pct` | numeric |  |  | KPI 4 Share of population aged 65+, %. |
| `businesses_total` | bigint |  |  | KPI 5 Total businesses: DENUE establishments in the AGEB. |
| `business_density_km2` | numeric |  |  | KPI 6 Business density: businesses_total / area_km2. |
| `businesses_per_1000` | numeric |  |  | KPI 7 Businesses per 1,000 residents: 1000 x businesses_total / pop_total. |
| `retail_density_km2` | numeric |  |  | KPI 8 Retail density: retail establishments (SCIAN 46) / area_km2. |
| `service_density_km2` | numeric |  |  | KPI 9 Service density: service establishments (SCIAN 51-81) / area_km2. |
| `dominant_sector` | text |  |  | KPI 10 Dominant economic activity: sector with most establishments. |
| `dominant_sector_share_pct` | numeric |  |  | Share of the AGEB establishments in the dominant sector, %. |
| `dominant_sector_tied` | boolean |  |  | True when two or more sectors tie for first place. |
| `crimes_total` | bigint |  |  | KPI 11 Total crime incidents assigned to the AGEB; NULL when no crime source is loaded. |
| `crime_rate_per_1000` | numeric |  |  | KPI 12 Crime rate: 1000 x crimes_total / pop_total. |
| `crimes_per_100_businesses` | numeric |  |  | KPI 14 Crime relative to business activity: 100 x crimes_total / businesses_total. |
| `has_suppressed` | boolean |  |  | True when the census withheld at least one value of the AGEB. |
| `no_resident_population` | boolean |  |  | True when the AGEB has no resident population. |
| `low_population` | boolean |  |  | True when the AGEB has fewer than 100 residents. |

## vw_kpi_ageb_geo

*view* — Grain: one row per urban AGEB. vw_kpi_ageb plus the AGEB polygon.

| Column | Type | Key | Null | Description |
|---|---|---|---|---|
| `cvegeo` | character(13) |  |  | AGEB key. |
| `locality_name` | text |  |  | Locality the AGEB belongs to. |
| `area_km2` | numeric |  |  | AGEB area, km². |
| `pop_total` | integer |  |  | KPI 1 Total population. |
| `pop_density_km2` | numeric |  |  | KPI 2 Population density: pop_total / area_km2. |
| `pea_rate_pct` | numeric |  |  | KPI 3 Economically active population rate: 100 x PEA / population aged 12+. |
| `share_0_14_pct` | numeric |  |  | KPI 4 Share of population aged 0-14, %. |
| `share_15_64_pct` | numeric |  |  | KPI 4 Share of population aged 15-64, %. |
| `share_65_plus_pct` | numeric |  |  | KPI 4 Share of population aged 65+, %. |
| `businesses_total` | bigint |  |  | KPI 5 Total businesses: DENUE establishments in the AGEB. |
| `business_density_km2` | numeric |  |  | KPI 6 Business density: businesses_total / area_km2. |
| `businesses_per_1000` | numeric |  |  | KPI 7 Businesses per 1,000 residents: 1000 x businesses_total / pop_total. |
| `retail_density_km2` | numeric |  |  | KPI 8 Retail density: retail establishments (SCIAN 46) / area_km2. |
| `service_density_km2` | numeric |  |  | KPI 9 Service density: service establishments (SCIAN 51-81) / area_km2. |
| `dominant_sector` | text |  |  | KPI 10 Dominant economic activity: sector with most establishments. |
| `dominant_sector_share_pct` | numeric |  |  | Share of the AGEB establishments in the dominant sector, %. |
| `dominant_sector_tied` | boolean |  |  | True when two or more sectors tie for first place. |
| `crimes_total` | bigint |  |  | KPI 11 Total crime incidents assigned to the AGEB; NULL when no crime source is loaded. |
| `crime_rate_per_1000` | numeric |  |  | KPI 12 Crime rate: 1000 x crimes_total / pop_total. |
| `crimes_per_100_businesses` | numeric |  |  | KPI 14 Crime relative to business activity: 100 x crimes_total / businesses_total. |
| `has_suppressed` | boolean |  |  | True when the census withheld at least one value of the AGEB. |
| `no_resident_population` | boolean |  |  | True when the AGEB has no resident population. |
| `low_population` | boolean |  |  | True when the AGEB has fewer than 100 residents. |
| `geom` | geometry(MultiPolygon,4326) |  |  | AGEB polygon in WGS84. |

## vw_kpi_city

*view* — Grain: one row for the whole study area. Totals and city-wide ratios.

| Column | Type | Key | Null | Description |
|---|---|---|---|---|
| `agebs` | bigint |  |  | Number of urban AGEBs in the study area. |
| `area_km2` | numeric |  |  | AGEB area, km². |
| `pop_total` | bigint |  |  | KPI 1 Total population. |
| `pop_density_km2` | numeric |  |  | KPI 2 Population density: pop_total / area_km2. |
| `businesses_total` | bigint |  |  | KPI 5 Total businesses: DENUE establishments in the AGEB. |
| `business_density_km2` | numeric |  |  | KPI 6 Business density: businesses_total / area_km2. |
| `businesses_per_1000` | numeric |  |  | KPI 7 Businesses per 1,000 residents: 1000 x businesses_total / pop_total. |
| `crimes_total` | bigint |  |  | KPI 11 Total crime incidents assigned to the AGEB; NULL when no crime source is loaded. |
| `crime_rate_per_1000` | numeric |  |  | KPI 12 Crime rate: 1000 x crimes_total / pop_total. |

## vw_population_by_age

*view* — Grain: AGEB x age group. Population counts and shares of the AGEB total.

| Column | Type | Key | Null | Description |
|---|---|---|---|---|
| `cvegeo` | character(13) |  |  | AGEB key. |
| `age_group` | text |  |  | Age group: 0-14, 15-64 or 65+. |
| `age_order` | integer |  |  | Sort order of the age group. |
| `population` | integer |  |  | Population of the age group; NULL when withheld by the census. |
| `share_pct` | numeric |  |  | Share of the AGEB population, %. |
