# KPI validation

Results of `sql/05_kpi_validation_queries.sql` run against the warehouse on 2026-10-05. Every value below comes from `dw` tables and views.

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
| NULL | 0 | True |

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

## KPI 11-M — Total Crime Incidents (municipal)

*SESNSP incidents per year, municipality of Mérida*

| year | months_reported | crimes_total |
|---|---|---|
| 2015 | 12 | 21829 |
| 2016 | 12 | 21345 |
| 2017 | 12 | 15452 |
| 2018 | 12 | 8740 |
| 2019 | 12 | 11283 |
| 2020 | 12 | 6530 |
| 2021 | 12 | 6522 |
| 2022 | 12 | 1820 |
| 2023 | 12 | 1994 |
| 2024 | 12 | 2003 |
| 2025 | 12 | 3135 |

## KPI 12-M — Crime Rate (municipal)

*incidents per 1,000 residents of the municipality (population 2020)*

| year | crimes_total | crime_rate_per_1000 |
|---|---|---|
| 2020 | 6530 | 6.56 |
| 2021 | 6522 | 6.55 |
| 2022 | 1820 | 1.83 |
| 2023 | 1994 | 2.0 |
| 2024 | 2003 | 2.01 |
| 2025 | 3135 | 3.15 |

## KPI 13-M — Incidents by Type and Time (municipal)

*latest full year, by legal good affected and quarter*

| crime_group | q1 | q2 | q3 | q4 | total |
|---|---|---|---|---|---|
| Property | 296 | 334 | 349 | 322 | 1301 |
| Other | 155 | 197 | 290 | 315 | 957 |
| Life and bodily integrity | 66 | 59 | 131 | 141 | 397 |
| Family | 79 | 99 | 91 | 83 | 352 |
| Sexual freedom and safety | 38 | 28 | 41 | 18 | 125 |
| Society | 0 | 1 | 0 | 1 | 2 |
| Personal liberty | 0 | 0 | 1 | 0 | 1 |

## KPI 14-M — Crime relative to Business Activity (municipal)

*incidents per 100 establishments*

| year | crimes_total | businesses_total | crimes_per_100_businesses |
|---|---|---|---|
| 2020 | 6530 | 56664 | 11.52 |
| 2021 | 6522 | 56664 | 11.51 |
| 2022 | 1820 | 56664 | 3.21 |
| 2023 | 1994 | 56664 | 3.52 |
| 2024 | 2003 | 56664 | 3.53 |
| 2025 | 3135 | 56664 | 5.53 |

## Warehouse totals against the cleaned sources

*load audit*

| item | source_value | warehouse_value |
|---|---|---|
| census_population | 957399 | 957399 |
| crime_clean_rows | 0 | 0 |
| crime_municipal_incidents | 100653 | 100653 |
| denue_clean_rows | 56909 | 56909 |
