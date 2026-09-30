# KPI validation

Results of `sql/05_kpi_validation_queries.sql` run against the warehouse on 2026-09-30. Every value below comes from `dw` tables and views.

## KPI 1 — Total Population

*city total and the five most populated AGEBs*

| scope | pop_total |
|---|---|
| Study area | 957399 |
| 3105000016825 | 7244 |
| 3105000013074 | 5926 |
| 310500001060A | 5888 |
| 3105000016045 | 5529 |
| 3105000012907 | 5184 |

## KPI 2 — Population Density

*inhabitants per km², city and distribution across AGEBs*

| city_density_km2 | median_ageb_density_km2 | max_ageb_density_km2 |
|---|---|---|
| 3684.2 | 4513.1 | 18064.5 |

## KPI 3 — Economically Active Population Rate

*100 x PEA / population aged 12+*

| city_pea_rate_pct | mean_ageb_pea_rate_pct | agebs_not_available |
|---|---|---|
| 63.16 | 63.53 | 10 |

## KPI 4 — Population by Age Group

*counts and shares for the study area*

| age_group | population | share_pct |
|---|---|---|
| 0-14 | 190473 | 19.89 |
| 15-64 | 670763 | 70.06 |
| 65+ | 93599 | 9.78 |

## KPI 5 — Total Businesses

*DENUE establishments assigned to the study area*

| businesses_total | fact_rows |
|---|---|
| 56664 | 56664 |

## KPI 6 — Business Density

*establishments per km²*

| city_business_density_km2 | median_ageb_business_density_km2 |
|---|---|
| 218.1 | 224.8 |

## KPI 7 — Businesses per 1,000 Residents

*excluding AGEBs with fewer than 100 residents*

| city_businesses_per_1000 | median_ageb_businesses_per_1000 | agebs_flagged_low_population |
|---|---|---|
| 59.19 | 46.725 | 32 |

## KPI 8 — Retail Density

*retail establishments (SCIAN 46) per km²*

| retail_establishments | city_retail_density_km2 |
|---|---|
| 19342 | 74.4 |

## KPI 9 — Service Density

*service establishments (SCIAN 51-81) per km²*

| service_establishments | city_service_density_km2 |
|---|---|
| 29355 | 113.0 |

## KPI 10 — Dominant Economic Activity

*number of AGEBs where each sector dominates*

| dominant_sector | agebs |
|---|---|
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

## KPI 11 — Total Crime Incidents

*incidents assigned to the study area*

| crimes_total | fact_rows | crime_source_loaded |
|---|---|---|
| NULL | 0 | False |

## KPI 12 — Crime Rate

*incidents per 1,000 residents*

| city_crime_rate_per_1000 | median_ageb_crime_rate_per_1000 |
|---|---|
| NULL | NULL |

## KPI 13 — Incidents by Type and Time

*by crime group and part of the day*

_No rows: the layer is not loaded._

## KPI 14 — Crime relative to Business Activity

*incidents per 100 establishments*

| city_crimes_per_100_businesses | median_ageb_crimes_per_100_businesses |
|---|---|
| NULL | NULL |

## Warehouse totals against the cleaned sources

*load audit*

| item | source_value | warehouse_value |
|---|---|---|
| census_population | 957399 | 957399 |
| crime_clean_rows | 0 | 0 |
| denue_clean_rows | 56909 | 56909 |
