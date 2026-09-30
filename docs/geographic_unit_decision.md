# Geographic unit decision

**Selected unit: urban AGEB** (*Área Geoestadística Básica urbana*), INEGI Marco Geoestadístico,
2020 Census edition. **Study area:** the 526 urban AGEBs of the municipality of Mérida (`31050`),
259.9 km², which hold 957,399 of the 995,129 inhabitants of the municipality (96.2%).

All figures below are produced by `notebooks/01_data_geographic_assessment.ipynb` and stored in
`outputs/phase1_assessment.json`.

## Why the sources need a common unit

| Source | Native geographic representation |
|---|---|
| Census 2020 | tabular rows keyed by state, municipality, locality, AGEB and block codes |
| DENUE | one point per establishment (latitude/longitude) plus declared AGEB and block keys |
| Cartography | polygons keyed by `CVEGEO` |
| Crime incidents | one point per incident (latitude/longitude), no administrative key |

Points can be assigned to any polygon layer, but census indicators exist only for INEGI's own
units. The unit therefore has to be one for which the census publishes results.

## Alternatives evaluated

| Criterion | Block (manzana) | **Urban AGEB** | Colonia | Locality |
|---|---|---|---|---|
| Official INEGI polygons | yes, 17,595 | **yes, 526** | not published | yes, 53 |
| Census results with a matching key | yes | **yes, 526 of 526 match** | no | yes |
| Median population per unit | 52 | **1,755** | — | — |
| Economically active population withheld | 4.8% of blocks | **0.8% of AGEBs** | — | — |
| Population 65+ withheld | 23.5% of blocks | **2.7% of AGEBs** | — | — |
| Units without any establishment | 33.0% | **3.0%** | — | — |

- **Block — rejected.** Confidentiality withholds age-group and activity values in a large share
  of blocks, a third of them contain no business, and rates computed on about fifty residents are
  unstable. Incident counts per block would be mostly zero.
- **Colonia — rejected.** It is the unit residents recognise, but INEGI publishes neither colonia
  polygons nor census results by colonia. Using it would mean relying on a non-official boundary
  layer and estimating population by areal interpolation, which adds an error that cannot be
  validated.
- **Locality — rejected.** One locality (Mérida, `0001`) contains 483 of the 526 AGEBs, so the
  unit shows almost no variation inside the city.
- **Urban AGEB — selected.** Official polygons and census results share the same key with a
  complete one-to-one match, confidentiality affects under 3% of units in any required variable,
  and 526 units are adequate for correlation and spatial-autocorrelation statistics.

## Polygon inspection

| Check | Result |
|---|---|
| Coordinate reference system | `MEXICO_ITRF_2008_LCC`, metres; projection parameters identical to EPSG:6372 |
| Geometry type | Polygon |
| Invalid geometries | 0 |
| Duplicate `CVEGEO` | 0 |
| Census keys without polygon / polygons without census row | 0 / 0 |

The shapefile `.prj` has no EPSG code, so the layer is declared explicitly as EPSG:6372. Areas are
computed in that CRS; stored geometries and point sources use EPSG:4326.

## Latitude/longitude to polygon integration

Tested with the 56,909 DENUE establishments of the municipality, all with valid coordinates:

| Result | Establishments |
|---|---|
| Assigned to an urban AGEB (`within`) | 56,664 (99.57%) |
| Not inside any urban AGEB | 245 |
| — of which declared by INEGI in a non-urban AGEB | 165 |
| Points inside more than one polygon | 0 |
| Spatial AGEB equal to the AGEB declared by INEGI | 56,560 (99.82% of assigned) |

The independent key declared by DENUE confirms the spatial join. The 245 unassigned
establishments lie outside the study area or marginally outside a polygon edge; they are kept in
an audit table and excluded from AGEB indicators. Crime incidents follow the same procedure.

## Limitations of the choice

- **Modifiable areal unit problem.** Results depend on AGEB boundaries and size; another unit
  could yield different coefficients.
- **Heterogeneous size.** Central AGEBs are small and dense, peripheral ones large; densities are
  used instead of raw counts when comparing areas.
- **Non-residential AGEBs.** Some AGEBs have very few residents (industrial or institutional
  land); per-capita indicators there are reported as not available rather than as extreme values.
- **Reference dates.** Census polygons and population refer to 2020; establishments and incidents
  are more recent, so urban growth after 2020 outside these polygons is not covered.
