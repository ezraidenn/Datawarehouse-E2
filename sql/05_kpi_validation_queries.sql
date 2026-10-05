-- =============================================================================
-- 05_kpi_validation_queries.sql — one query per required KPI, run against the
-- warehouse only. Each block starts with a "-- @kpi" header line used by
-- src/validate_kpis.py to label the results in outputs/kpi_validation.md.
-- =============================================================================

-- @kpi 1 | Total Population | city total and the five most populated AGEBs
SELECT 'Study area' AS scope, sum(pop_total) AS pop_total FROM dw.vw_kpi_ageb
UNION ALL
(SELECT cvegeo, pop_total FROM dw.vw_kpi_ageb ORDER BY pop_total DESC NULLS LAST LIMIT 5);

-- @kpi 2 | Population Density | inhabitants per km², city and distribution across AGEBs
SELECT (SELECT pop_density_km2 FROM dw.vw_kpi_city) AS city_density_km2,
       percentile_cont(0.5) WITHIN GROUP (ORDER BY pop_density_km2) AS median_ageb_density_km2,
       max(pop_density_km2) AS max_ageb_density_km2
FROM dw.vw_kpi_ageb;

-- @kpi 3 | Economically Active Population Rate | 100 x PEA / population aged 12+
SELECT round(100.0 * sum(d.pop_econ_active) / sum(d.pop_12_plus), 2) AS city_pea_rate_pct,
       (SELECT round(avg(pea_rate_pct), 2) FROM dw.vw_kpi_ageb) AS mean_ageb_pea_rate_pct,
       (SELECT count(*) FROM dw.vw_kpi_ageb WHERE pea_rate_pct IS NULL) AS agebs_not_available
FROM dw.fact_demographics d
WHERE d.pop_econ_active IS NOT NULL AND d.pop_12_plus IS NOT NULL;

-- @kpi 4 | Population by Age Group | counts and shares for the study area
SELECT age_group, sum(population) AS population,
       round(100.0 * sum(population) / (SELECT sum(pop_total) FROM dw.fact_demographics), 2) AS share_pct
FROM dw.vw_population_by_age
GROUP BY age_group, age_order
ORDER BY age_order;

-- @kpi 5 | Total Businesses | DENUE establishments assigned to the study area
SELECT (SELECT businesses_total FROM dw.vw_kpi_city) AS businesses_total,
       (SELECT count(*) FROM dw.fact_establishment) AS fact_rows;

-- @kpi 6 | Business Density | establishments per km²
SELECT (SELECT business_density_km2 FROM dw.vw_kpi_city) AS city_business_density_km2,
       percentile_cont(0.5) WITHIN GROUP (ORDER BY business_density_km2) AS median_ageb_business_density_km2
FROM dw.vw_kpi_ageb;

-- @kpi 7 | Businesses per 1,000 Residents | excluding AGEBs with fewer than 100 residents
SELECT (SELECT businesses_per_1000 FROM dw.vw_kpi_city) AS city_businesses_per_1000,
       percentile_cont(0.5) WITHIN GROUP (ORDER BY businesses_per_1000) AS median_ageb_businesses_per_1000,
       (SELECT count(*) FROM dw.vw_kpi_ageb WHERE low_population) AS agebs_flagged_low_population
FROM dw.vw_kpi_ageb
WHERE NOT low_population;

-- @kpi 8 | Retail Density | retail establishments (SCIAN 46) per km²
SELECT count(*) FILTER (WHERE a.sector_group = 'retail') AS retail_establishments,
       round(count(*) FILTER (WHERE a.sector_group = 'retail')
             / (SELECT sum(area_km2) FROM dw.dim_geography), 1) AS city_retail_density_km2
FROM dw.fact_establishment f
JOIN dw.dim_activity a USING (activity_key);

-- @kpi 9 | Service Density | service establishments (SCIAN 51-81) per km²
SELECT count(*) FILTER (WHERE a.sector_group = 'service') AS service_establishments,
       round(count(*) FILTER (WHERE a.sector_group = 'service')
             / (SELECT sum(area_km2) FROM dw.dim_geography), 1) AS city_service_density_km2
FROM dw.fact_establishment f
JOIN dw.dim_activity a USING (activity_key);

-- @kpi 10 | Dominant Economic Activity | number of AGEBs where each sector dominates
SELECT coalesce(dominant_sector, '(no establishments)') AS dominant_sector, count(*) AS agebs
FROM dw.vw_kpi_ageb
GROUP BY dominant_sector
ORDER BY agebs DESC;

-- @kpi 11 | Total Crime Incidents | incidents assigned to the study area
SELECT (SELECT crimes_total FROM dw.vw_kpi_city) AS crimes_total,
       (SELECT count(*) FROM dw.fact_crime_incident) AS fact_rows,
       EXISTS (SELECT 1 FROM dw.dim_source WHERE layer = 'public_safety') AS crime_source_loaded;

-- @kpi 12 | Crime Rate | incidents per 1,000 residents
SELECT (SELECT crime_rate_per_1000 FROM dw.vw_kpi_city) AS city_crime_rate_per_1000,
       percentile_cont(0.5) WITHIN GROUP (ORDER BY crime_rate_per_1000) AS median_ageb_crime_rate_per_1000
FROM dw.vw_kpi_ageb
WHERE NOT low_population;

-- @kpi 13 | Incidents by Type and Time | by crime group and part of the day
SELECT crime_group, day_part, sum(incidents) AS incidents
FROM dw.vw_crime_by_type_time
GROUP BY crime_group, day_part
ORDER BY crime_group, day_part;

-- @kpi 14 | Crime relative to Business Activity | incidents per 100 establishments
SELECT round(100.0 * sum(crimes_total) / sum(businesses_total), 2) AS city_crimes_per_100_businesses,
       percentile_cont(0.5) WITHIN GROUP (ORDER BY crimes_per_100_businesses) AS median_ageb_crimes_per_100_businesses
FROM dw.vw_kpi_ageb;

-- @kpi 11-M | Total Crime Incidents (municipal) | SESNSP incidents per year, municipality of Mérida
SELECT year, months_reported, crimes_total
FROM dw.vw_kpi_crime_municipal_year
ORDER BY year;

-- @kpi 12-M | Crime Rate (municipal) | incidents per 1,000 residents of the municipality (population 2020)
SELECT year, crimes_total, crime_rate_per_1000
FROM dw.vw_kpi_crime_municipal_year
WHERE year >= 2020
ORDER BY year;

-- @kpi 13-M | Incidents by Type and Time (municipal) | latest full year, by legal good affected and quarter
SELECT crime_group, sum(incidents) FILTER (WHERE month <= 3) AS q1, sum(incidents) FILTER (WHERE month BETWEEN 4 AND 6) AS q2,
       sum(incidents) FILTER (WHERE month BETWEEN 7 AND 9) AS q3, sum(incidents) FILTER (WHERE month >= 10) AS q4,
       sum(incidents) AS total
FROM dw.vw_crime_municipal_month
WHERE year = (SELECT max(year) FROM dw.vw_kpi_crime_municipal_year WHERE months_reported = 12)
GROUP BY crime_group
ORDER BY total DESC;

-- @kpi 14-M | Crime relative to Business Activity (municipal) | incidents per 100 establishments
SELECT year, crimes_total, businesses_total, crimes_per_100_businesses
FROM dw.vw_kpi_crime_municipal_year
WHERE year >= 2020
ORDER BY year;

-- @kpi reconciliation | Warehouse totals against the cleaned sources | load audit
SELECT a.item,
       a.value AS source_value,
       CASE a.item
           WHEN 'census_population' THEN (SELECT sum(pop_total) FROM dw.fact_demographics)
           WHEN 'denue_clean_rows' THEN (SELECT count(*) FROM dw.fact_establishment)
                                     + (SELECT count(*) FROM staging.unmatched_points WHERE layer = 'establishment')
           WHEN 'crime_clean_rows' THEN (SELECT count(*) FROM dw.fact_crime_incident)
                                     + (SELECT count(*) FROM staging.unmatched_points WHERE layer = 'crime_incident')
           WHEN 'crime_municipal_incidents' THEN (SELECT sum(incidents) FROM dw.fact_crime_municipal)
       END AS warehouse_value
FROM staging.load_audit a
ORDER BY a.item;
