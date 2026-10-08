# Warehouse profile

## Row counts
| Object | Type | Rows | Grain |
|---|---|---:|---|
| dim_activity | table | 744 | Grain: one row per SCIAN activity class present in DENUE for Mérida. |
| dim_business_size | table | 7 | Grain: one row per DENUE employment stratum (per_ocu). |
| dim_crime_type | table | 55 | Grain: one row per crime category published by the incident source. |
| dim_date | table | 3,989 | Grain: one row per calendar day of the incident period; key yyyymmdd, 0 = unknown date. |
| dim_geography | table | 526 | Grain: one row per urban AGEB of the municipality of Mérida (Marco Geoestadístico 2020). Conformed dimension shared by all facts. |
| dim_municipality | table | 1 | Grain: one row per municipality (Mérida). Geography of the municipal crime counts, which have no location inside the city. |
| dim_source | table | 4 | Grain: one row per original dataset. Provenance of every fact row. |
| dim_time_of_day | table | 25 | Grain: one row per hour of the day (0-23); -1 = unknown time. |
| fact_crime_incident | table | 0 | Grain: one row per georeferenced crime incident located inside an urban AGEB of Mérida. |
| fact_crime_municipal | table | 12,936 | Grain: one municipality x month x crime modality (SESNSP). Incidents without location: they describe the municipality as a whole and are never assigned to AGEBs. |
| fact_demographics | table | 526 | Grain: one row per urban AGEB, Census 2020 (AGEB total rows published by INEGI). |
| fact_establishment | table | 56,664 | Grain: one row per DENUE establishment located inside an urban AGEB of Mérida. |
| vw_activity_by_ageb | view | 5,396 | Grain: AGEB x SCIAN sector (by name). Establishment counts and rank within the AGEB; ties broken by sector code. |
| vw_crime_by_type_time | view | 0 | Grain: AGEB x crime type x year x month x weekday x part of day. Incident counts. |
| vw_crime_municipal_month | view | 12,936 | Grain: municipality x month x crime modality. KPI 13 (incidents by type and time) at municipal level. |
| vw_kpi_ageb | view | 526 | Grain: one row per urban AGEB. The scalar KPIs of the project; KPI 13 (incidents by type and time) is dw.vw_crime_by_type_time. |
| vw_kpi_ageb_geo | view | 526 | Grain: one row per urban AGEB. vw_kpi_ageb plus the AGEB polygon. |
| vw_kpi_city | view | 1 | Grain: one row for the whole study area. Totals and city-wide ratios. |
| vw_kpi_crime_municipal_year | view | 11 | Grain: municipality x year. Crime KPIs 11, 12 and 14 at municipal level; rates use the 2020 municipal population and the current establishments, so they are approximations for years far from those references. |
| vw_population_by_age | view | 1,578 | Grain: AGEB x age group. Population counts and shares of the AGEB total. |

## Main totals
| Measure | Value |
|---|---:|
| Total population | 957,399 |
| Total establishments | 56,664 |
| Retail establishments | 19,342 |
| Service establishments | 29,355 |
| AGEBs without establishments | 18 |

## Dominant activity
| dominant_sector | agebs |
|---|---:|
| Retail trade | 417 |
| Other services (except government) | 38 |
| (no establishments) | 18 |
| Accommodation and food services | 15 |
| Manufacturing | 12 |
| Health care and social assistance | 12 |
| Wholesale trade | 7 |
| Professional, scientific and technical services | 3 |
| Real estate and rental | 2 |
| Construction | 1 |
| Government and international organisations | 1 |

Retail trade dominates most AGEBs, with 417 of 526 AGEBs in the study area showing it as the leading sector.

## Load checks
- rows: dim_geography = staging.geography — PASS
- rows: fact_demographics = staging.census_ageb — PASS
- rows: fact_establishment = staging.establishment — PASS
- rows: fact_crime_incident = staging.crime_incident — PASS
- keys: every census AGEB has a polygon and every polygon a census row — PASS
- integrity: no orphan establishment rows — PASS
- integrity: no orphan crime rows — PASS
- reconcile: warehouse population = census AGEB totals — PASS
- reconcile: establishments + unmatched = cleaned DENUE rows — PASS
- reconcile: incidents + unmatched = cleaned crime rows — PASS
- geometry: AGEB polygons valid, SRID 4326, positive area — PASS
- geometry: every establishment point lies in its AGEB polygon — PASS
- audit: spatial AGEB agrees with DENUE declared AGEB (>= 95%) — PASS
- coverage: georeferenced crime source loaded — WARN
- reconcile: municipal crime incidents = cleaned SESNSP total — PASS
- rows: fact_crime_municipal = staging.crime_municipal — PASS
