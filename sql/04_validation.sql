-- =============================================================================
-- 04_validation.sql — load checks. Returns one row per check with PASS, WARN or
-- FAIL. The pipeline stops when any check is FAIL.
-- staging.load_audit holds the row counts written by the Python ETL.
-- =============================================================================

WITH audit AS (
    SELECT item, value FROM staging.load_audit
),
checks AS (
    -- 1. Row counts: every staging row reached the warehouse -----------------------
    SELECT 1 AS n, 'rows: dim_geography = staging.geography' AS check_name,
           (SELECT count(*) FROM dw.dim_geography) = (SELECT count(*) FROM staging.geography) AS ok,
           false AS warn_only,
           format('%s vs %s', (SELECT count(*) FROM dw.dim_geography), (SELECT count(*) FROM staging.geography)) AS detail
    UNION ALL
    SELECT 2, 'rows: fact_demographics = staging.census_ageb',
           (SELECT count(*) FROM dw.fact_demographics) = (SELECT count(*) FROM staging.census_ageb), false,
           format('%s vs %s', (SELECT count(*) FROM dw.fact_demographics), (SELECT count(*) FROM staging.census_ageb))
    UNION ALL
    SELECT 3, 'rows: fact_establishment = staging.establishment',
           (SELECT count(*) FROM dw.fact_establishment) = (SELECT count(*) FROM staging.establishment), false,
           format('%s vs %s', (SELECT count(*) FROM dw.fact_establishment), (SELECT count(*) FROM staging.establishment))
    UNION ALL
    SELECT 4, 'rows: fact_crime_incident = staging.crime_incident',
           (SELECT count(*) FROM dw.fact_crime_incident) = (SELECT count(*) FROM staging.crime_incident), false,
           format('%s vs %s', (SELECT count(*) FROM dw.fact_crime_incident), (SELECT count(*) FROM staging.crime_incident))

    -- 2. Keys -----------------------------------------------------------------------
    UNION ALL
    SELECT 5, 'keys: every census AGEB has a polygon and every polygon a census row',
           NOT EXISTS (SELECT cvegeo FROM staging.census_ageb EXCEPT SELECT cvegeo FROM dw.dim_geography)
           AND NOT EXISTS (SELECT cvegeo FROM dw.dim_geography EXCEPT SELECT cvegeo FROM staging.census_ageb), false,
           format('%s census keys without polygon, %s polygons without census row',
                  (SELECT count(*) FROM (SELECT cvegeo FROM staging.census_ageb EXCEPT SELECT cvegeo FROM dw.dim_geography) x),
                  (SELECT count(*) FROM (SELECT cvegeo FROM dw.dim_geography EXCEPT SELECT cvegeo FROM staging.census_ageb) y))

    -- 3. Referential integrity (declared foreign keys make orphans impossible; checked
    --    explicitly as evidence) --------------------------------------------------------
    UNION ALL
    SELECT 6, 'integrity: no orphan establishment rows',
           NOT EXISTS (SELECT 1 FROM dw.fact_establishment f
                       LEFT JOIN dw.dim_geography g USING (geography_key)
                       LEFT JOIN dw.dim_activity a USING (activity_key)
                       LEFT JOIN dw.dim_business_size z USING (size_key)
                       WHERE g.geography_key IS NULL OR a.activity_key IS NULL OR z.size_key IS NULL), false, ''
    UNION ALL
    SELECT 7, 'integrity: no orphan crime rows',
           NOT EXISTS (SELECT 1 FROM dw.fact_crime_incident f
                       LEFT JOIN dw.dim_geography g USING (geography_key)
                       LEFT JOIN dw.dim_crime_type t USING (crime_type_key)
                       LEFT JOIN dw.dim_date d USING (date_key)
                       LEFT JOIN dw.dim_time_of_day h USING (time_key)
                       WHERE g.geography_key IS NULL OR t.crime_type_key IS NULL
                          OR d.date_key IS NULL OR h.time_key IS NULL), false, ''

    -- 4. Reconciliation with the cleaned sources ------------------------------------
    UNION ALL
    SELECT 8, 'reconcile: warehouse population = census AGEB totals',
           (SELECT sum(pop_total) FROM dw.fact_demographics) = (SELECT value FROM audit WHERE item = 'census_population'), false,
           format('%s vs %s', (SELECT sum(pop_total) FROM dw.fact_demographics), (SELECT value FROM audit WHERE item = 'census_population'))
    UNION ALL
    SELECT 9, 'reconcile: establishments + unmatched = cleaned DENUE rows',
           (SELECT count(*) FROM dw.fact_establishment)
             + (SELECT count(*) FROM staging.unmatched_points WHERE layer = 'establishment')
             = (SELECT value FROM audit WHERE item = 'denue_clean_rows'), false,
           format('%s + %s vs %s', (SELECT count(*) FROM dw.fact_establishment),
                  (SELECT count(*) FROM staging.unmatched_points WHERE layer = 'establishment'),
                  (SELECT value FROM audit WHERE item = 'denue_clean_rows'))
    UNION ALL
    SELECT 10, 'reconcile: incidents + unmatched = cleaned crime rows',
           (SELECT count(*) FROM dw.fact_crime_incident)
             + (SELECT count(*) FROM staging.unmatched_points WHERE layer = 'crime_incident')
             = (SELECT value FROM audit WHERE item = 'crime_clean_rows'), false,
           format('%s + %s vs %s', (SELECT count(*) FROM dw.fact_crime_incident),
                  (SELECT count(*) FROM staging.unmatched_points WHERE layer = 'crime_incident'),
                  (SELECT value FROM audit WHERE item = 'crime_clean_rows'))

    -- 5. Geometry ---------------------------------------------------------------------
    UNION ALL
    SELECT 11, 'geometry: AGEB polygons valid, SRID 4326, positive area',
           NOT EXISTS (SELECT 1 FROM dw.dim_geography
                       WHERE NOT ST_IsValid(geom) OR ST_SRID(geom) <> 4326 OR area_km2 <= 0), false, ''
    UNION ALL
    SELECT 12, 'geometry: every establishment point lies in its AGEB polygon',
           NOT EXISTS (SELECT 1 FROM dw.fact_establishment f JOIN dw.dim_geography g USING (geography_key)
                       WHERE NOT ST_Intersects(g.geom, f.geom)), false, ''

    -- 6. Spatial-join audit against the AGEB declared by DENUE -------------------------
    UNION ALL
    SELECT 13, 'audit: spatial AGEB agrees with DENUE declared AGEB (>= 95%)',
           (SELECT avg((g.cvegeo = f.denue_cvegeo)::int) FROM dw.fact_establishment f
            JOIN dw.dim_geography g USING (geography_key)) >= 0.95, true,
           format('%s%% agreement', (SELECT round(100 * avg((g.cvegeo = f.denue_cvegeo)::int), 2)
                                     FROM dw.fact_establishment f JOIN dw.dim_geography g USING (geography_key)))
    UNION ALL
    SELECT 14, 'coverage: crime source loaded',
           EXISTS (SELECT 1 FROM dw.dim_source WHERE layer = 'public_safety'), true,
           CASE WHEN EXISTS (SELECT 1 FROM dw.dim_source WHERE layer = 'public_safety')
                THEN '' ELSE 'crime KPIs are NULL until the incident source is added' END
)
SELECT n, check_name,
       CASE WHEN ok THEN 'PASS' WHEN warn_only THEN 'WARN' ELSE 'FAIL' END AS status,
       detail
FROM checks
ORDER BY n;
