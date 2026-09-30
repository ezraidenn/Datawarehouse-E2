-- =============================================================================
-- 03_views.sql — KPI views. Every reported indicator is computed here, from the
-- warehouse tables only.
--
-- Conventions
--   * Densities are per square kilometre (area measured in EPSG:6372).
--   * Rates and shares are percentages.
--   * A KPI whose denominator is zero or unknown is NULL, never zero.
--   * Crime KPIs are NULL for every AGEB while no crime source is loaded, so that
--     "no data" is never confused with "no incidents".
--   * low_population flags AGEBs with fewer than 100 residents, where per-capita
--     KPIs are extreme.
-- =============================================================================

-- Population by age group: one row per AGEB and age group ------------------------
CREATE OR REPLACE VIEW dw.vw_population_by_age AS
SELECT g.cvegeo, a.age_group, a.age_order, a.population,
       round(100.0 * a.population / NULLIF(d.pop_total, 0), 2) AS share_pct
FROM dw.fact_demographics d
JOIN dw.dim_geography g USING (geography_key)
CROSS JOIN LATERAL (VALUES
    ('0-14', 1, d.pop_0_14),
    ('15-64', 2, d.pop_15_64),
    ('65+', 3, d.pop_65_plus)
) AS a (age_group, age_order, population);
COMMENT ON VIEW dw.vw_population_by_age IS 'Grain: AGEB x age group. Population counts and shares of the AGEB total.';

-- Establishments by sector: one row per AGEB and sector ---------------------------
CREATE OR REPLACE VIEW dw.vw_activity_by_ageb AS
SELECT g.cvegeo, a.sector_name, min(a.sector_code) AS first_sector_code, a.sector_group,
       count(*) AS establishments,
       rank() OVER (PARTITION BY g.cvegeo
                    ORDER BY count(*) DESC, min(a.sector_code)) AS rank_in_ageb
FROM dw.fact_establishment f
JOIN dw.dim_geography g USING (geography_key)
JOIN dw.dim_activity a USING (activity_key)
GROUP BY g.cvegeo, a.sector_name, a.sector_group;
COMMENT ON VIEW dw.vw_activity_by_ageb IS 'Grain: AGEB x SCIAN sector (by name). Establishment counts and rank within the AGEB; ties broken by sector code.';

-- Incidents by type and time: one row per AGEB, type, month and part of day --------
CREATE OR REPLACE VIEW dw.vw_crime_by_type_time AS
SELECT g.cvegeo, t.crime_type, t.crime_group, d.year, d.month, d.month_name,
       d.day_name, d.is_weekend, h.day_part,
       sum(f.incident_count) AS incidents
FROM dw.fact_crime_incident f
JOIN dw.dim_geography g USING (geography_key)
JOIN dw.dim_crime_type t USING (crime_type_key)
JOIN dw.dim_date d USING (date_key)
JOIN dw.dim_time_of_day h USING (time_key)
GROUP BY g.cvegeo, t.crime_type, t.crime_group, d.year, d.month, d.month_name,
         d.day_name, d.is_weekend, h.day_part;
COMMENT ON VIEW dw.vw_crime_by_type_time IS 'Grain: AGEB x crime type x year x month x weekday x part of day. Incident counts.';

-- All scalar KPIs: one row per AGEB ------------------------------------------------
CREATE OR REPLACE VIEW dw.vw_kpi_ageb AS
WITH crime_loaded AS (
    SELECT EXISTS (SELECT 1 FROM dw.dim_source WHERE layer = 'public_safety') AS ok
),
business AS (
    SELECT f.geography_key,
           count(*) AS businesses_total,
           count(*) FILTER (WHERE a.sector_group = 'retail') AS businesses_retail,
           count(*) FILTER (WHERE a.sector_group = 'service') AS businesses_service
    FROM dw.fact_establishment f
    JOIN dw.dim_activity a USING (activity_key)
    GROUP BY f.geography_key
),
crime AS (
    SELECT geography_key, sum(incident_count) AS crimes_total
    FROM dw.fact_crime_incident
    GROUP BY geography_key
),
dominant AS (
    SELECT v.cvegeo, v.sector_name, v.establishments,
           count(*) OVER (PARTITION BY v.cvegeo) AS tied
    FROM dw.vw_activity_by_ageb v
    WHERE v.rank_in_ageb = 1
),
base AS (
    SELECT g.geography_key, g.cvegeo, g.locality_name, g.area_km2,
           d.pop_total, d.pop_0_14, d.pop_15_64, d.pop_65_plus, d.pop_12_plus,
           d.pop_econ_active, d.has_suppressed,
           coalesce(b.businesses_total, 0) AS businesses_total,
           coalesce(b.businesses_retail, 0) AS businesses_retail,
           coalesce(b.businesses_service, 0) AS businesses_service,
           CASE WHEN cl.ok THEN coalesce(c.crimes_total, 0) END AS crimes_total
    FROM dw.dim_geography g
    LEFT JOIN dw.fact_demographics d USING (geography_key)
    LEFT JOIN business b USING (geography_key)
    LEFT JOIN crime c USING (geography_key)
    CROSS JOIN crime_loaded cl
)
SELECT b.cvegeo,
       b.locality_name,
       round(b.area_km2, 4)                                                   AS area_km2,
       -- demographic
       b.pop_total,                                                                 -- KPI 1
       round(b.pop_total / b.area_km2, 1)                                     AS pop_density_km2,          -- KPI 2
       round(100.0 * b.pop_econ_active / NULLIF(b.pop_12_plus, 0), 2)         AS pea_rate_pct,             -- KPI 3
       round(100.0 * b.pop_0_14 / NULLIF(b.pop_total, 0), 2)                  AS share_0_14_pct,           -- KPI 4
       round(100.0 * b.pop_15_64 / NULLIF(b.pop_total, 0), 2)                 AS share_15_64_pct,          -- KPI 4
       round(100.0 * b.pop_65_plus / NULLIF(b.pop_total, 0), 2)               AS share_65_plus_pct,        -- KPI 4
       -- economic
       b.businesses_total,                                                          -- KPI 5
       round(b.businesses_total / b.area_km2, 1)                              AS business_density_km2,     -- KPI 6
       round(1000.0 * b.businesses_total / NULLIF(b.pop_total, 0), 2)         AS businesses_per_1000,      -- KPI 7
       round(b.businesses_retail / b.area_km2, 1)                             AS retail_density_km2,       -- KPI 8
       round(b.businesses_service / b.area_km2, 1)                            AS service_density_km2,      -- KPI 9
       dm.sector_name                                                         AS dominant_sector,          -- KPI 10
       round(100.0 * dm.establishments / NULLIF(b.businesses_total, 0), 2)    AS dominant_sector_share_pct,
       (dm.tied > 1)                                                          AS dominant_sector_tied,
       -- public safety
       b.crimes_total,                                                              -- KPI 11
       round(1000.0 * b.crimes_total / NULLIF(b.pop_total, 0), 2)             AS crime_rate_per_1000,      -- KPI 12
       round(100.0 * b.crimes_total / NULLIF(b.businesses_total, 0), 2)       AS crimes_per_100_businesses, -- KPI 14
       -- flags
       b.has_suppressed,
       (b.pop_total IS NULL OR b.pop_total = 0)                               AS no_resident_population,
       -- Per-capita KPIs on fewer than 100 residents are arithmetically valid but extreme
       -- (e.g. commercial centre AGEBs); the flag lets the analysis treat them explicitly.
       (b.pop_total < 100)                                                    AS low_population
FROM base b
LEFT JOIN LATERAL (
    SELECT sector_name, establishments, tied
    FROM dominant
    WHERE dominant.cvegeo = b.cvegeo
    ORDER BY sector_name
    LIMIT 1
) dm ON true;
COMMENT ON VIEW dw.vw_kpi_ageb IS 'Grain: one row per urban AGEB. The scalar KPIs of the project; KPI 13 (incidents by type and time) is dw.vw_crime_by_type_time.';

-- Same KPIs with the polygon, for maps and spatial weights -------------------------
CREATE OR REPLACE VIEW dw.vw_kpi_ageb_geo AS
SELECT k.*, g.geom
FROM dw.vw_kpi_ageb k
JOIN dw.dim_geography g USING (cvegeo);
COMMENT ON VIEW dw.vw_kpi_ageb_geo IS 'Grain: one row per urban AGEB. vw_kpi_ageb plus the AGEB polygon.';

-- City-level totals, used to reconcile with the sources ----------------------------
CREATE OR REPLACE VIEW dw.vw_kpi_city AS
SELECT count(*)                                                    AS agebs,
       round(sum(area_km2), 2)                                     AS area_km2,
       sum(pop_total)                                              AS pop_total,
       round(sum(pop_total) / sum(area_km2), 1)                    AS pop_density_km2,
       sum(businesses_total)                                       AS businesses_total,
       round(sum(businesses_total) / sum(area_km2), 1)             AS business_density_km2,
       round(1000.0 * sum(businesses_total) / sum(pop_total), 2)   AS businesses_per_1000,
       sum(crimes_total)                                           AS crimes_total,
       round(1000.0 * sum(crimes_total) / sum(pop_total), 2)       AS crime_rate_per_1000
FROM dw.vw_kpi_ageb;
COMMENT ON VIEW dw.vw_kpi_city IS 'Grain: one row for the whole study area. Totals and city-wide ratios.';
