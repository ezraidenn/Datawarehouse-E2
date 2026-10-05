"""Build the technical report (docs/report/technical_report.pdf).

Every figure and number is read from the files produced by the pipeline and the analysis
(outputs/ and docs/), so the report always matches the warehouse.

Requires Google Chrome or Chromium for the HTML-to-PDF step (CHROME env var to override).

Usage: python docs/report/build_report.py
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src import config  # noqa: E402

HERE = Path(__file__).resolve().parent
HTML_OUT = HERE / "technical_report.html"
PDF_OUT = HERE / "technical_report.pdf"
META = json.loads((HERE / "report_meta.json").read_text(encoding="utf-8"))

O = config.OUTPUTS
phase1 = json.loads((O / "phase1_assessment.json").read_text(encoding="utf-8"))
join = json.loads((O / "spatial_join_report.json").read_text(encoding="utf-8"))
checks = json.loads((O / "load_validation.json").read_text(encoding="utf-8"))
manifest = json.loads(config.SOURCE_MANIFEST.read_text(encoding="utf-8"))
corr = pd.read_csv(O / "correlations.csv")
moran = pd.read_csv(O / "moran_results.csv")
crime_city = O / "crime_municipal_summary.json"
crime = json.loads(crime_city.read_text(encoding="utf-8")) if crime_city.exists() else None


def img(rel: str) -> str:
    return (ROOT / rel).resolve().as_uri()


def n(v, d=0) -> str:
    return f"{v:,.{d}f}"


def kpi_city() -> dict:
    from src.analysis.dw_io import read_from_dw
    city = read_from_dw("vw_kpi_city").iloc[0].to_dict()
    kpi = read_from_dw("vw_kpi_ageb")
    pop = read_from_dw("vw_population_by_age").groupby("age_group")["population"].sum()
    dem = read_from_dw("fact_demographics")
    city["pea_rate"] = 100 * dem["pop_econ_active"].sum() / dem["pop_12_plus"].sum()
    city["age"] = {k: 100 * v / city["pop_total"] for k, v in pop.items()}
    city["retail"] = int((kpi["retail_density_km2"] * kpi["area_km2"]).round().sum())
    city["dominant_retail"] = int((kpi["dominant_sector"] == "Retail trade").sum())
    city["low_pop"] = int(kpi["low_population"].sum())
    city["suppressed"] = int(kpi["has_suppressed"].sum())
    return city


city = kpi_city()
est = join["establishments"]
cand = phase1["candidate_units"]
g = moran[moran["analysis"] == "global Moran's I"].set_index("x")
lisa = moran[moran["analysis"] == "LISA"].set_index("x")
bv = moran[moran["analysis"] == "bivariate Moran's I"].iloc[0]
c = corr.set_index(["x", "y"])
passed = sum(1 for r in checks if r["status"] == "PASS")
warned = [r["check_name"] for r in checks if r["status"] == "WARN"]

LABEL = {
    "pop_density_km2": "Population density", "business_density_km2": "Business density",
    "pea_rate_pct": "Economically active population rate", "businesses_per_1000": "Businesses per 1,000 residents",
    "share_65_plus_pct": "Population aged 65+", "service_density_km2": "Service density",
    "crime_rate_per_1000": "Crime rate", "crimes_total": "Crime incidents",
}

corr_rows = "".join(
    f"<tr><td>{LABEL.get(r.x, r.x)}</td><td>{LABEL.get(r.y, r.y)}</td><td class='r'>{r.n}</td>"
    f"<td class='r'><b>{r.spearman_rho:+.2f}</b></td><td class='r'>{r.pearson_r_log:+.2f}</td>"
    f"<td class='r'>{'&lt; 0.001' if r.spearman_p < 0.001 else f'{r.spearman_p:.3f}'}</td></tr>"
    for r in corr.itertuples())
moran_rows = "".join(
    f"<tr><td>{LABEL.get(x, x)}</td><td class='r'>{int(r['n'])}</td><td class='r'><b>{r['statistic']:.3f}</b></td>"
    f"<td class='r'>{r['z_sim']:.1f}</td><td class='r'>{r['p_sim']:.3f}</td></tr>" for x, r in g.iterrows())

if crime:
    crime_section = f"""
<h3>Public safety at municipal level</h3>
<p>No dataset with incident coordinates is published for Mérida; the most detailed official source is the
monthly municipal incidence of the SESNSP. It enters the warehouse as a separate fact table at
municipality × month × crime-type grain. In {crime['year']} the municipality recorded
<b>{n(crime['incidents_year'])}</b> incidents of the common jurisdiction, <b>{crime['rate_per_1000']:.1f}</b>
per 1,000 residents and <b>{crime['per_100_businesses']:.1f}</b> per 100 establishments;
{crime['top_type_share']:.0f}% were {crime['top_type'].lower()}. Because these counts have no location,
they cannot be assigned to AGEBs, and the AGEB-level crime KPIs and spatial statistics remain empty by design;
the point-level path is implemented and tested for when georeferenced data become available.</p>
<figure><img src="{img('outputs/figures/crime_municipal_trend.png')}" style="width:88%"><figcaption>Figure 6.
Monthly crime incidents in the municipality of Mérida by crime group (SESNSP).</figcaption></figure>"""
else:
    crime_section = """
<h3>Public safety</h3>
<p>No dataset with incident coordinates is published for Mérida. The crime path of the warehouse is
implemented and tested, and the crime KPIs remain NULL until a georeferenced source is supplied.</p>"""

HTML = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Mérida Urban Intelligence — Technical report</title>
<style>
@page {{ size: A4; margin: 16mm 16mm 16mm 16mm; }}
* {{ box-sizing: border-box; }}
body {{ font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif; color: #1F2A36; font-size: 9.6pt; line-height: 1.45; margin: 0; }}
h1 {{ font-size: 22pt; font-weight: 700; color: #0B3C5D; margin: 0; letter-spacing: -0.01em; }}
.sub {{ color: #5B6773; font-size: 10pt; margin-top: 2px; }}
.meta {{ color: #5B6773; font-size: 8.6pt; margin-top: 8px; }}
.rule {{ height: 4px; background: linear-gradient(90deg, #225EA8, #41B6C4, #C7E9B4); margin: 10px 0 4px; }}
h2 {{ font-size: 12.5pt; font-weight: 700; color: #0B3C5D; margin: 14px 0 4px; }}
h2 span {{ color: #41B6C4; margin-right: 6px; }}
h3 {{ font-size: 10pt; font-weight: 600; color: #225EA8; margin: 10px 0 2px; }}
p {{ margin: 3px 0 6px; text-align: justify; }}
table {{ border-collapse: collapse; width: 100%; font-size: 8.4pt; margin: 4px 0 8px; }}
th {{ text-align: left; background: #EDF8FB; color: #0B3C5D; font-weight: 600; padding: 3px 6px; }}
td {{ padding: 2.5px 6px; border-bottom: 1px solid #E3E9EF; vertical-align: top; }}
td.r, th.r {{ text-align: right; white-space: nowrap; }}
.tiles {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; margin: 6px 0 8px; }}
.tile {{ background: #EDF8FB; border-left: 4px solid #225EA8; border-radius: 4px; padding: 6px 9px; }}
.tile b {{ display: block; font-size: 15pt; font-weight: 700; color: #0B3C5D; line-height: 1.15; }}
.tile span {{ font-size: 7.8pt; color: #5B6773; }}
figure {{ margin: 6px 0 8px; text-align: center; break-inside: avoid; }}
figure img {{ max-width: 100%; }}
figcaption {{ font-size: 7.8pt; color: #5B6773; margin-top: 2px; }}
.two {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; align-items: start; }}
.finding {{ border-left: 3px solid #41B6C4; padding-left: 8px; margin: 6px 0; }}
.pb {{ break-before: page; }}
ul {{ margin: 2px 0 6px 0; padding: 0; list-style: none; }} li {{ margin: 2px 0; position: relative; padding-left: 14px; }}
li::before {{ content: ""; position: absolute; left: 2px; top: 6px; width: 5px; height: 5px; border-radius: 1px; background: #41B6C4; }}
code {{ font-size: 8.4pt; background: #F2F5F8; padding: 0 3px; border-radius: 2px; }}
</style></head><body>

<h1>Mérida Urban Intelligence</h1>
<div class="sub">Geospatial Data Warehouse · Technical report · Unit 2 Project</div>
<div class="meta">{META['course']} · {META['program']} · {META['university']}<br>
{' · '.join(META['team'])} · {META['date']}</div>
<div class="rule"></div>

<h2><span>1</span>Problem and data sources</h2>
<p>Mérida's demographic, economic, cartographic and public-safety data come from different institutions
and describe the city in incompatible ways: census results are tables keyed by statistical areas, business
and incident records are points, and boundaries are polygons. None of the sources can answer, on its own,
whether population, economic activity and insecurity follow the same geography. The project integrates them
into a single PostgreSQL/PostGIS warehouse that calculates territorial KPIs, compares areas and tests their
spatial association; every number in this report is computed from that warehouse.</p>
<table><tr><th>Layer</th><th>Source</th><th>Original grain</th><th class="r">Records for Mérida</th></tr>
<tr><td>Demographic</td><td>INEGI Population and Housing Census 2020, results by urban AGEB and block</td><td>block, with AGEB totals</td><td class="r">{n(phase1['census_rows_municipality'])} rows</td></tr>
<tr><td>Economic</td><td>INEGI DENUE (registrations up to {phase1['denue_fecha_alta_max']})</td><td>establishment (point)</td><td class="r">{n(phase1['denue_rows_municipality'])} establishments</td></tr>
<tr><td>Geographic</td><td>INEGI Marco Geoestadístico 2020</td><td>polygon</td><td class="r">{n(phase1['ageb_polygons'])} urban AGEBs</td></tr>
<tr><td>Public safety</td><td>{'SESNSP municipal crime incidence (no coordinates published for Mérida)' if crime else 'georeferenced incidents (not available for Mérida)'}</td><td>{'municipality × month × crime type' if crime else 'incident (point)'}</td><td class="r">{n(crime['rows']) + ' rows' if crime else '—'}</td></tr></table>

<h2><span>2</span>Geographic integration strategy</h2>
<p>The unit of analysis had to be one for which the census publishes results, so that points could be
related to residents. Four candidates were measured on the downloaded data.</p>
<table><tr><th>Candidate</th><th class="r">Units</th><th class="r">Median population</th><th class="r">PEA withheld</th><th class="r">Units without business</th><th>Decision</th></tr>
<tr><td>Block (manzana)</td><td class="r">{n(cand['block (manzana)']['units in Mérida'])}</td><td class="r">{n(cand['block (manzana)']['median population'])}</td><td class="r">{cand['block (manzana)']['PEA not available (%)']:.1f}%</td><td class="r">{cand['block (manzana)']['units without any business (%)']:.0f}%</td><td>too small, unstable rates</td></tr>
<tr><td><b>Urban AGEB</b></td><td class="r"><b>{n(cand['urban AGEB']['units in Mérida'])}</b></td><td class="r"><b>{n(cand['urban AGEB']['median population'])}</b></td><td class="r"><b>{cand['urban AGEB']['PEA not available (%)']:.1f}%</b></td><td class="r"><b>{cand['urban AGEB']['units without any business (%)']:.0f}%</b></td><td><b>selected</b></td></tr>
<tr><td>Colonia</td><td class="r">—</td><td class="r">—</td><td class="r">—</td><td class="r">—</td><td>no official polygons or census data</td></tr>
<tr><td>Locality</td><td class="r">{n(cand['locality']['units in Mérida'])}</td><td class="r">—</td><td class="r">—</td><td class="r">—</td><td>one locality holds 483 AGEBs</td></tr></table>
<p>The study area is the {n(phase1['ageb_polygons'])} urban AGEBs of the municipality ({phase1['ageb_area_km2_total']:.1f} km²),
home to {n(phase1['population_sum_ageb'])} of its {n(phase1['population_municipality'])} inhabitants
({100 * phase1['population_sum_ageb'] / phase1['population_municipality']:.1f}%). Census and polygon keys match one to
one. The cartography's projection has no EPSG code; its parameters were verified to equal EPSG:6372, where areas
are measured, while geometries are stored in EPSG:4326 like the point sources. Points are assigned with a
point-in-polygon rule (boundary points to the lowest key, unmatched points kept with a reason):
<b>{est['match_rate_pct']:.2f}%</b> of {n(est['points'])} establishments fall inside an AGEB, and
<b>{est['declared_ageb_agreement_pct']:.2f}%</b> of them agree with the AGEB that INEGI declares for the
establishment, an independent confirmation of the join. Of the {est['unmatched']} unmatched, {est['unmatched_declared_rural']}
are declared in rural areas.</p>

<h2><span>3</span>Data Warehouse architecture</h2>
<p>A batch pipeline moves the data <b>RAW → CLEAN → SPATIAL JOIN → PostgreSQL/PostGIS</b>. Raw files are
checksummed and never edited; Python cleans and joins; SQL scripts rebuild a <code>staging</code> schema and
the dimensional schema <code>dw</code>, create the KPI views and run {len(checks)} validation checks
({passed} pass{', ' + str(len(warned)) + ' warning' if warned else ''}) covering row counts, keys, referential integrity,
reconciliation with the sources and geometry. A second run reproduces identical results.</p>
<p>The model is a <b>constellation schema</b>: three fact tables with explicit grain share the conformed
dimension <code>dim_geography</code>, which is what allows indicators that combine layers.</p>
<table><tr><th>Fact</th><th>Grain</th></tr>
<tr><td>fact_demographics</td><td>one urban AGEB, census 2020</td></tr>
<tr><td>fact_establishment</td><td>one DENUE establishment</td></tr>
<tr><td>fact_crime_incident</td><td>one georeferenced incident</td></tr>
{'<tr><td>fact_crime_municipal</td><td>municipality × month × crime type</td></tr>' if crime else ''}</table>
<figure><img src="{img('docs/warehouse_overview.png')}" style="width:82%"><figcaption>Figure 1. Facts and dimensions,
coloured by thematic layer.</figcaption></figure>

<h2><span>4</span>Key KPIs and spatial analysis</h2>
<p>The fourteen required KPIs are SQL views with explicit rules: densities per km², rates in percent, and
NULL instead of zero when a denominator is zero or unknown. AGEBs with fewer than 100 residents ({city['low_pop']})
are flagged because per-capita values there are extreme, and the {city['suppressed']} AGEBs where the census
withholds a value keep it as missing.</p>
<div class="tiles">
<div class="tile"><b>{n(city['pop_total'])}</b><span>residents · {n(city['pop_density_km2'])} per km²</span></div>
<div class="tile"><b>{n(city['businesses_total'])}</b><span>establishments · {n(city['business_density_km2'])} per km²</span></div>
<div class="tile"><b>{city['businesses_per_1000']:.1f}</b><span>businesses per 1,000 residents</span></div>
<div class="tile"><b>{city['pea_rate']:.1f}%</b><span>economically active population rate</span></div></div>
<p>Retail trade is the dominant activity in {city['dominant_retail']} of the {n(phase1['ageb_polygons'])} AGEBs;
{city['age']['65+']:.1f}% of residents are 65 or older. Relationships between indicators are measured with Spearman's ρ,
robust to the skewed distributions, and checked with Pearson's r on log values. Spatial structure is measured
with Moran's I under <b>Queen contiguity</b> (AGEBs sharing an edge or vertex are neighbours), row-standardised
weights, log values and 999 permutations; the two detached AGEBs with no neighbour are excluded. Only touching
AGEBs influence each other, so neighbours across a road reserve are ignored, and large peripheral AGEBs, with
fewer neighbours, give less stable local results.</p>

<h2><span>5</span>Main findings</h2>
<div class="finding"><b>Business activity concentrates in the centre; residents live around it.</b>
Population and business density are positively related (ρ = {c.loc[('pop_density_km2', 'business_density_km2'), 'spearman_rho']:.2f}),
but per resident the relation reverses: the densest residential AGEBs have fewer businesses per 1,000 inhabitants
(ρ = {c.loc[('pop_density_km2', 'businesses_per_1000'), 'spearman_rho']:.2f}).</div>
<div class="two">
<figure><img src="{img('outputs/maps/01_population_density.png')}"><figcaption>Figure 2. Population density (quintiles).</figcaption></figure>
<figure><img src="{img('outputs/maps/04_business_density.png')}"><figcaption>Figure 3. Business density (quintiles).</figcaption></figure></div>
<div class="finding"><b>Indicators cluster strongly in space.</b> All tested indicators show positive and significant
global Moran's I; business density forms {int(lisa.loc['business_density_km2', 'n_high_high'])} High-High AGEBs over the
historic centre and its extensions and {int(lisa.loc['business_density_km2', 'n_low_low'])} Low-Low AGEBs on the northern periphery.</div>
<div class="two"><div>
<table><tr><th>Indicator</th><th class="r">n</th><th class="r">Moran's I</th><th class="r">z</th><th class="r">p</th></tr>{moran_rows}</table>
<table><tr><th>x</th><th>y</th><th class="r">n</th><th class="r">ρ</th><th class="r">r (log)</th><th class="r">p</th></tr>{corr_rows}</table>
</div><figure><img src="{img('outputs/maps/lisa_02_business_density_km2.png')}"><figcaption>Figure 4. LISA clusters of
business density (p &lt; 0.05).</figcaption></figure></div>
<div class="finding"><b>Business activity sits next to populated areas, and services next to older ones.</b>
Bivariate Moran's I between business density and the population density of neighbouring AGEBs is
{bv['statistic']:.2f} (p = {bv['p_sim']:.3f}); AGEBs with older populations have higher service density
(ρ = {c.loc[('share_65_plus_pct', 'service_density_km2'), 'spearman_rho']:.2f}), and AGEBs with a higher economically
active rate have fewer businesses per resident (ρ = {c.loc[('pea_rate_pct', 'businesses_per_1000'), 'spearman_rho']:.2f}),
the profile of newer dormitory neighbourhoods.</div>
<figure><img src="{img('outputs/maps/bilisa_01_business_density_km2__pop_density_km2.png')}" style="width:58%"><figcaption>Figure 5.
Bivariate LISA: business density against neighbouring population density.</figcaption></figure>
{crime_section}

<h2><span>6</span>Limitations and interpretation cautions</h2>
<ul>
<li><b>Association, not causation.</b> Correlations and Moran statistics describe how areas co-vary in space.</li>
<li><b>Spatial dependence.</b> Because neighbouring AGEBs are similar, ordinary p-values of the correlations overstate the evidence.</li>
<li><b>Ecological fallacy and MAUP.</b> Results describe AGEBs, not people or firms, and could change with other boundaries.</li>
<li><b>Different reference dates.</b> Population and boundaries are from 2020, establishments from the latest DENUE{', crime from ' + str(crime['year']) if crime else ''}.</li>
<li><b>Coverage.</b> DENUE under-represents informal and home-based activity; {est['unmatched']} establishments outside the 2020 urban AGEBs are excluded.</li>
<li><b>Public safety.</b> Without published incident coordinates, crime cannot be analysed inside the city; the warehouse is ready for a point-level source.</li>
<li><b>Neighbourhood rule.</b> Queen contiguity ignores proximity across gaps; another rule could change which AGEBs are flagged locally.</li>
</ul>
</body></html>"""


def chrome() -> str:
    for candidate in (os.environ.get("CHROME"), shutil.which("chrome"), shutil.which("chromium"),
                      r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                      r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"):
        if candidate and Path(candidate).exists():
            return candidate
    raise SystemExit("Chrome/Chromium not found; set CHROME")


def main() -> None:
    HTML_OUT.write_text(HTML, encoding="utf-8")
    subprocess.run([chrome(), "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                    "--virtual-time-budget=8000", f"--print-to-pdf={PDF_OUT}", HTML_OUT.as_uri()],
                   check=True, capture_output=True)
    print(f"report written to {PDF_OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
