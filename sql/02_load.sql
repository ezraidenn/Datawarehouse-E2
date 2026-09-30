-- =============================================================================
-- 02_load.sql — populate the dimensional model from the staging schema.
-- Runs after the Python ETL has loaded staging.*; see src/load_dw.py.
-- =============================================================================

-- Sources -----------------------------------------------------------------------
INSERT INTO dw.dim_source (source_code, layer, source_name, provider, edition, url,
                           download_date, original_grain, file_name, sha256)
SELECT source_code, layer, source_name, provider, edition, url,
       download_date::date, original_grain, file_name, sha256
FROM staging.source
ORDER BY source_code;

-- Geography ---------------------------------------------------------------------
INSERT INTO dw.dim_geography (cvegeo, cve_ent, cve_mun, cve_loc, cve_ageb, municipality_name,
                              locality_name, area_km2, geom, centroid, source_key)
SELECT g.cvegeo, g.cve_ent, g.cve_mun, g.cve_loc, g.cve_ageb, g.municipality_name,
       g.locality_name, g.area_km2,
       ST_Multi(g.geometry)::geometry(MultiPolygon, 4326),
       ST_PointOnSurface(g.geometry)::geometry(Point, 4326),
       s.source_key
FROM staging.geography g
CROSS JOIN (SELECT source_key FROM dw.dim_source WHERE source_code = 'geography') s
ORDER BY g.cvegeo;

-- Activity (SCIAN) --------------------------------------------------------------
INSERT INTO dw.dim_activity (scian_code, activity_name, sector_code, sector_name, sector_group)
SELECT scian_code, min(activity_name), min(sector_code), min(sector_name), min(sector_group)
FROM staging.establishment
GROUP BY scian_code
ORDER BY scian_code;

-- Business size -----------------------------------------------------------------
INSERT INTO dw.dim_business_size (size_label, size_order, min_employees, max_employees)
SELECT size_label, size_order, min_employees, max_employees
FROM staging.size_class
ORDER BY size_order;

-- Crime type --------------------------------------------------------------------
INSERT INTO dw.dim_crime_type (crime_type, crime_group)
SELECT crime_type, min(crime_group)
FROM staging.crime_incident
GROUP BY crime_type
ORDER BY crime_type;

-- Date: unknown member plus every day between the first and last incident --------
INSERT INTO dw.dim_date (date_key, day_name, month_name)
VALUES (0, 'unknown', 'unknown');

INSERT INTO dw.dim_date (date_key, full_date, year, quarter, month, month_name, day,
                         day_of_week, day_name, is_weekend)
SELECT to_char(d, 'YYYYMMDD')::integer, d::date,
       extract(year FROM d), extract(quarter FROM d), extract(month FROM d),
       trim(to_char(d, 'Month')), extract(day FROM d),
       extract(isodow FROM d), trim(to_char(d, 'Day')), extract(isodow FROM d) IN (6, 7)
FROM (
    SELECT generate_series(min(to_date(date_key::text, 'YYYYMMDD')),
                           max(to_date(date_key::text, 'YYYYMMDD')),
                           interval '1 day') AS d
    FROM staging.crime_incident
    WHERE date_key <> 0
) days;

-- Time of day -------------------------------------------------------------------
INSERT INTO dw.dim_time_of_day (time_key, hour, day_part)
VALUES (-1, NULL, 'unknown');

INSERT INTO dw.dim_time_of_day (time_key, hour, day_part)
SELECT h, h,
       CASE WHEN h < 6 THEN 'early morning'
            WHEN h < 12 THEN 'morning'
            WHEN h < 19 THEN 'afternoon'
            ELSE 'night' END
FROM generate_series(0, 23) AS h;

-- Fact: demographics ------------------------------------------------------------
INSERT INTO dw.fact_demographics (geography_key, source_key, pop_total, pop_0_14, pop_15_64,
                                  pop_65_plus, pop_12_plus, pop_econ_active, pop_employed,
                                  dwellings_total, dwellings_inhabited, avg_occupants,
                                  has_suppressed)
SELECT g.geography_key, s.source_key, c.pop_total, c.pop_0_14, c.pop_15_64, c.pop_65_plus,
       c.pop_12_plus, c.pop_econ_active, c.pop_employed, c.dwellings_total,
       c.dwellings_inhabited, c.avg_occupants, c.has_suppressed
FROM staging.census_ageb c
JOIN dw.dim_geography g ON g.cvegeo = c.cvegeo
CROSS JOIN (SELECT source_key FROM dw.dim_source WHERE source_code = 'census') s;

-- Fact: establishments ----------------------------------------------------------
INSERT INTO dw.fact_establishment (denue_id, geography_key, activity_key, size_key, source_key,
                                   establishment_name, denue_cvegeo, join_method, geom)
SELECT e.denue_id, g.geography_key, a.activity_key, z.size_key, s.source_key,
       e.establishment_name, e.denue_cvegeo, e.join_method,
       e.geometry::geometry(Point, 4326)
FROM staging.establishment e
JOIN dw.dim_geography g ON g.cvegeo = e.cvegeo
JOIN dw.dim_activity a ON a.scian_code = e.scian_code
JOIN dw.dim_business_size z ON z.size_label = e.size_label
CROSS JOIN (SELECT source_key FROM dw.dim_source WHERE source_code = 'denue') s
ORDER BY e.denue_id;

-- Fact: crime incidents ---------------------------------------------------------
INSERT INTO dw.fact_crime_incident (source_incident_id, geography_key, crime_type_key, date_key,
                                    time_key, source_key, location_precision, join_method, geom)
SELECT i.source_incident_id, g.geography_key, t.crime_type_key, i.date_key, i.time_key,
       s.source_key, i.location_precision, i.join_method, i.geometry::geometry(Point, 4326)
FROM staging.crime_incident i
JOIN dw.dim_geography g ON g.cvegeo = i.cvegeo
JOIN dw.dim_crime_type t ON t.crime_type = i.crime_type
CROSS JOIN (SELECT source_key FROM dw.dim_source WHERE source_code = 'crime') s
ORDER BY i.source_incident_id;

ANALYZE dw.dim_geography;
ANALYZE dw.fact_establishment;
ANALYZE dw.fact_crime_incident;
