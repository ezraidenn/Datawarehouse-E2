"""Build the presentation (docs/presentation/slides.pdf, 16:9).

All numbers are read from outputs/ and the warehouse views, like the technical report.
Requires Google Chrome or Chromium (CHROME env var to override).

Usage: python docs/presentation/build_slides.py
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
from src.analysis.dw_io import read_from_dw  # noqa: E402

HERE = Path(__file__).resolve().parent
HTML_OUT = HERE / "slides.html"
PDF_OUT = HERE / "slides.pdf"
META = json.loads((ROOT / "docs" / "report" / "report_meta.json").read_text(encoding="utf-8"))

O = config.OUTPUTS
phase1 = json.loads((O / "phase1_assessment.json").read_text(encoding="utf-8"))
est = json.loads((O / "spatial_join_report.json").read_text(encoding="utf-8"))["establishments"]
checks = json.loads((O / "load_validation.json").read_text(encoding="utf-8"))
corr = pd.read_csv(O / "correlations.csv").set_index(["x", "y"])
moran = pd.read_csv(O / "moran_results.csv")
crime_file = O / "crime_municipal_summary.json"
crime = json.loads(crime_file.read_text(encoding="utf-8")) if crime_file.exists() else None
city = read_from_dw("vw_kpi_city").iloc[0]
kpi = read_from_dw("vw_kpi_ageb")
dem = read_from_dw("fact_demographics")
age = read_from_dw("vw_population_by_age").groupby("age_group")["population"].sum() / city["pop_total"] * 100
cand = phase1["candidate_units"]
g = moran[moran["analysis"] == "global Moran's I"].set_index("x")
lisa = moran[moran["analysis"] == "LISA"].set_index("x")
bv = moran[moran["analysis"] == "bivariate Moran's I"].iloc[0]
passed = sum(r["status"] == "PASS" for r in checks)
warned = sum(r["status"] == "WARN" for r in checks)
pea_rate = 100 * dem["pop_econ_active"].sum() / dem["pop_12_plus"].sum()


def img(rel: str) -> str:
    return (ROOT / rel).resolve().as_uri()


def n(v, d=0) -> str:
    return f"{v:,.{d}f}"


def slide(kicker: str, title: str, body: str, number: int) -> str:
    return (f'<section class="slide"><div class="bar"></div><div class="kicker">{kicker}</div>'
            f'<h1>{title}</h1>{body}<div class="foot"><span>Mérida Urban Intelligence</span>'
            f'<span>{number} / 12</span></div></section>')


def tile(value: str, label: str) -> str:
    return f'<div class="tile"><b>{value}</b><span>{label}</span></div>'


S = []

S.append(f"""<section class="slide cover"><div class="bar"></div>
<div class="kicker">Unit 2 Project · Geospatial Data Warehouse</div>
<h1 class="big">Mérida Urban Intelligence</h1>
<p class="lead">Integrating census, business, cartographic and public-safety data on one geography
to measure, compare and explain the city, AGEB by AGEB.</p>
<div class="team">{'<br>'.join(META['team'])}</div>
<div class="meta">{META['course']} · {META['program']}<br>{META['university']} · {META['date']}</div>
<img class="covermap" src="{img('outputs/maps/04_business_density.png')}"></section>""")

S.append(slide("1 · The problem", "Four official sources, four incompatible geographies", f"""
<div class="cards4">
<div class="card"><h3>Demographic</h3><p>INEGI Census 2020</p><em>tables by block and AGEB</em><b>{n(phase1['census_rows_municipality'])} rows</b></div>
<div class="card"><h3>Economic</h3><p>INEGI DENUE</p><em>points: one per establishment</em><b>{n(phase1['denue_rows_municipality'])} establishments</b></div>
<div class="card"><h3>Geographic</h3><p>INEGI Marco Geoestadístico 2020</p><em>polygons</em><b>{n(phase1['ageb_polygons'])} urban AGEBs</b></div>
<div class="card"><h3>Public safety</h3><p>{'SESNSP municipal incidence' if crime else 'Georeferenced incidents'}</p><em>{'counts by municipality and month' if crime else 'points: not published for Mérida'}</em><b>{n(crime['rows']) + ' rows' if crime else 'pending'}</b></div></div>
<p class="note">Goal: one warehouse in PostgreSQL/PostGIS that computes territorial KPIs, compares areas and tests
whether demographic, economic and public-safety patterns are geographically associated.</p>""", 2))

S.append(slide("1 · Geographic strategy", "Why the urban AGEB", f"""
<table class="t"><tr><th>Candidate</th><th>Units</th><th>Median population</th><th>PEA withheld</th><th>No business</th><th></th></tr>
<tr><td>Block</td><td>{n(cand['block (manzana)']['units in Mérida'])}</td><td>{n(cand['block (manzana)']['median population'])}</td><td>{cand['block (manzana)']['PEA not available (%)']:.1f}%</td><td>{cand['block (manzana)']['units without any business (%)']:.0f}%</td><td>too small</td></tr>
<tr class="sel"><td>Urban AGEB</td><td>{n(cand['urban AGEB']['units in Mérida'])}</td><td>{n(cand['urban AGEB']['median population'])}</td><td>{cand['urban AGEB']['PEA not available (%)']:.1f}%</td><td>{cand['urban AGEB']['units without any business (%)']:.0f}%</td><td>selected</td></tr>
<tr><td>Colonia</td><td>—</td><td>—</td><td>—</td><td>—</td><td>no census data</td></tr>
<tr><td>Locality</td><td>{n(cand['locality']['units in Mérida'])}</td><td>—</td><td>—</td><td>—</td><td>1 holds 483 AGEBs</td></tr></table>
<div class="tiles3">{tile(n(phase1['ageb_polygons']), 'urban AGEBs, keys match census 1:1')}{tile(f"{phase1['ageb_area_km2_total']:.1f} km²", 'study area')}{tile(f"{100 * phase1['population_sum_ageb'] / phase1['population_municipality']:.1f}%", 'of the municipal population covered')}</div>""", 3))

S.append(slide("2 · Spatial integration", "From latitude/longitude to AGEB", f"""
<div class="split"><div>
<div class="tiles1">{tile(f"{est['match_rate_pct']:.2f}%", f"of {n(est['points'])} establishments fall inside an AGEB polygon")}
{tile(f"{est['declared_ageb_agreement_pct']:.2f}%", 'agree with the AGEB declared by INEGI — independent check')}
{tile(n(est['unmatched']), f"unmatched, {est['unmatched_declared_rural']} declared in rural areas; kept with a reason")}</div>
<ul class="list"><li>Points built in EPSG:4326 from WGS84 coordinates</li><li>Rule: point within polygon; edge points to the lowest key</li>
<li>Cartography has no EPSG code → parameters verified equal to <b>EPSG:6372</b>; areas measured there</li></ul></div>
<img class="map" src="{img('outputs/maps/01_population_density.png')}"></div>""", 4))

S.append(slide("2 · ETL pipeline", "Reproducible from the original sources", f"""
<div class="flow"><div>RAW<span>INEGI downloads<br>checksummed, never edited</span></div><i>→</i>
<div>CLEAN<span>types, NULL for withheld values,<br>SCIAN sectors, duplicates</span></div><i>→</i>
<div>SPATIAL JOIN<span>points → AGEB,<br>audit of unmatched</span></div><i>→</i>
<div class="dw">POSTGIS DW<span>staging → star schema<br>→ KPI views</span></div></div>
<div class="tiles3">{tile(f"{passed} / {len(checks)}", f"validation checks pass ({warned} warning: crime coverage)")}{tile('1 command', 'python -m src.run_pipeline rebuilds everything')}{tile('identical', 'results on a second run (idempotent)')}</div>
<p class="note">Grain change made explicit: the census keeps INEGI's own AGEB totals instead of summing blocks,
because blocks withheld for confidentiality would make the sums fall short.</p>""", 5))

S.append(slide("2 · Data Warehouse", "Constellation schema on PostgreSQL/PostGIS", f"""
<img class="wide" src="{img('docs/warehouse_overview.png')}">
<div class="tiles4 facts">{tile('fact_demographics', '1 row = 1 urban AGEB (Census 2020)')}{tile('fact_establishment', '1 row = 1 DENUE establishment')}{tile('fact_crime_incident', '1 row = 1 georeferenced incident')}{tile('fact_crime_municipal', '1 row = municipality × month × crime modality')}</div>""", 6))

S.append(slide("3 · KPIs", "The 14 KPIs are SQL views on the warehouse", f"""
<div class="split kpis"><div class="tiles2">{tile(n(city['pop_total']), 'total population')}{tile(n(city['pop_density_km2']), 'inhabitants per km²')}
{tile(f"{pea_rate:.1f}%", 'economically active rate')}{tile(f"{age['65+']:.1f}%", 'aged 65 and over')}
{tile(n(city['businesses_total']), 'establishments')}{tile(n(city['business_density_km2']), 'establishments per km²')}
{tile(f"{city['businesses_per_1000']:.1f}", 'businesses per 1,000 residents')}{tile(str(int((kpi['dominant_sector'] == 'Retail trade').sum())), 'AGEBs dominated by retail')}</div>
<img class="map" src="{img('outputs/maps/08_dominant_activity.png')}"></div>
<p class="note">Rules: densities per km² · rates in % · NULL instead of zero when a denominator is missing ·
{int(kpi['low_population'].sum())} AGEBs with fewer than 100 residents flagged for per-capita KPIs ·
crime KPIs {'reported at municipal level (no coordinates published)' if crime else 'empty until a georeferenced source exists'}.</p>""", 7))

S.append(slide("3 · Geographic distribution", "Business concentrates in the centre; residents live around it", f"""
<div class="two"><img src="{img('outputs/maps/01_population_density.png')}"><img src="{img('outputs/maps/04_business_density.png')}"></div>""", 8))


def bar(label, rho):
    width = abs(rho) * 100
    side = "pos" if rho >= 0 else "neg"
    return (f'<div class="bar-row"><span class="bl">{label}</span><span class="track"><span class="{side}" '
            f'style="width:{width / 2:.1f}%"></span></span><b>{rho:+.2f}</b></div>')


pairs = [("pop_density_km2", "business_density_km2", "Population density ↔ business density"),
         ("share_65_plus_pct", "service_density_km2", "Population 65+ ↔ service density"),
         ("pop_density_km2", "businesses_per_1000", "Population density ↔ businesses per 1,000"),
         ("pea_rate_pct", "businesses_per_1000", "Economically active rate ↔ businesses per 1,000")]
S.append(slide("3 · Correlation", "Denser areas have more businesses, but fewer per resident", f"""
<div class="bars">{''.join(bar(lbl, corr.loc[(x, y), 'spearman_rho']) for x, y, lbl in pairs)}</div>
<p class="note">Spearman's ρ (skewed indicators), all p &lt; 0.001, n = 491–526 AGEBs; Pearson on log values agrees in sign.
Newer dormitory neighbourhoods: many working-age residents, few local businesses.</p>""", 9))

S.append(slide("4 · Spatial autocorrelation", "Every indicator clusters in space", f"""
<div class="split"><div>
<table class="t"><tr><th>Indicator</th><th>Moran's I</th><th>p</th></tr>
{''.join(f"<tr><td>{lbl}</td><td><b>{g.loc[x, 'statistic']:.2f}</b></td><td>{g.loc[x, 'p_sim']:.3f}</td></tr>" for x, lbl in [('pop_density_km2', 'Population density'), ('business_density_km2', 'Business density'), ('pea_rate_pct', 'Economically active rate'), ('businesses_per_1000', 'Businesses per 1,000')])}</table>
<ul class="list"><li>Queen contiguity, row-standardised, log values</li><li>999 permutations; 2 detached AGEBs excluded</li>
<li>LISA: <b>{int(lisa.loc['business_density_km2', 'n_high_high'])}</b> High-High AGEBs in the centre, <b>{int(lisa.loc['business_density_km2', 'n_low_low'])}</b> Low-Low on the northern edge</li></ul></div>
<img class="map" src="{img('outputs/maps/lisa_02_business_density_km2.png')}"></div>""", 10))

crime_text = (f"Municipal crime ({crime['year']}): <b>{n(crime['incidents_year'])}</b> incidents · "
              f"<b>{crime['rate_per_1000']:.1f}</b> per 1,000 residents · <b>{crime['per_100_businesses']:.1f}</b> per 100 "
              f"establishments (SESNSP). No coordinates are published, so crime cannot be placed in AGEBs."
              if crime else
              "No incident coordinates are published for Mérida (official data stop at municipal level). "
              "The crime path is built and tested; crime KPIs stay NULL — not zero — until a georeferenced source exists.")
S.append(slide("4 · Bivariate relationship and public safety", "Business sits next to populated areas", f"""
<div class="split"><div>
<div class="tiles1">{tile(f"{bv['statistic']:.2f}", f"bivariate Moran's I, business density vs neighbouring population density (p = {bv['p_sim']:.3f})")}</div>
<div class="callout"><h3>Public safety</h3><p>{crime_text}</p></div>
{f'<img class="chart" src="{img("outputs/figures/crime_municipal_types.png")}">' if crime else ''}</div>
<img class="map" src="{img('outputs/maps/bilisa_01_business_density_km2__pop_density_km2.png')}"></div>""", 11))

S.append(slide("4 · Conclusions", "What the warehouse shows, and what it cannot", """
<div class="two-text"><div><h3>Findings</h3><ul class="list">
<li>Economic activity is concentrated in the historic centre and corridors; residents live in a ring around it.</li>
<li>Per resident, the densest neighbourhoods have the fewest businesses: dormitory areas.</li>
<li>All indicators cluster in space; local clusters identify where to focus planning.</li>
<li>Older areas concentrate services.</li></ul></div>
<div><h3>Cautions</h3><ul class="list">
<li>Association is not causation; spatial dependence inflates ordinary p-values.</li>
<li>Results describe AGEBs, not people (ecological fallacy, MAUP).</li>
<li>Census 2020 vs current DENUE; informal activity under-represented.</li>
<li>Crime cannot be analysed inside the city without incident coordinates.</li></ul></div></div>""", 12))

HTML = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Mérida Urban Intelligence — slides</title>
<style>
@page {{ size: 1600px 900px; margin: 0; }}
* {{ box-sizing: border-box; }}
html, body {{ margin: 0; font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif; color: #1F2A36; }}
.slide {{ width: 1600px; height: 900px; position: relative; overflow: hidden; padding: 64px 90px 70px 100px; break-after: page; background: #fff; }}
.bar {{ position: absolute; left: 0; top: 0; bottom: 0; width: 14px; background: linear-gradient(#C7E9B4, #41B6C4, #225EA8); }}
.kicker {{ color: #225EA8; font-weight: 600; letter-spacing: .08em; text-transform: uppercase; font-size: 20px; }}
h1 {{ font-size: 46px; font-weight: 700; color: #0B3C5D; margin: 8px 0 30px; line-height: 1.12; }}
h1.big {{ font-size: 64px; margin-top: 150px; width: 800px; }}
h3 {{ color: #0B3C5D; margin: 0 0 10px; font-size: 28px; }}
.lead {{ font-size: 26px; color: #3D4A57; width: 780px; line-height: 1.4; }}
.team {{ margin-top: 40px; font-size: 22px; font-weight: 600; color: #0B3C5D; line-height: 1.5; }}
.meta {{ margin-top: 18px; font-size: 17px; color: #5B6773; line-height: 1.5; }}
.covermap {{ position: absolute; right: 40px; top: 190px; width: 620px; }}
.foot {{ position: absolute; left: 100px; right: 90px; bottom: 26px; display: flex; justify-content: space-between; font-size: 15px; color: #8A949E; }}
.tile {{ background: #EDF8FB; border-left: 6px solid #225EA8; border-radius: 6px; padding: 22px 26px; }}
.tile b {{ display: block; font-size: 46px; font-weight: 700; color: #0B3C5D; line-height: 1.1; }}
.tile span {{ font-size: 20px; color: #5B6773; }}
.tiles1 {{ display: grid; gap: 16px; }}
.tiles3 {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 18px; margin-top: 26px; }}
.tiles4 {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 18px; }}
.tiles2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }} .tiles2 .tile b {{ font-size: 44px; }} .kpis {{ grid-template-columns: 700px 1fr; }} .kpis .map {{ margin-top: 0; max-height: 560px; }}
.tiles4 {{ row-gap: 26px; }} .tiles4.facts .tile {{ padding: 20px 22px; }} .tiles4.facts {{ gap: 14px; }} .tiles4.facts .tile b {{ font-size: 23px; }} .tiles4.facts .tile span {{ font-size: 18px; }} .tiles4 .tile {{ padding: 34px 28px; }} .tiles4 .tile b {{ font-size: 54px; }}
.cards4 {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; }}
.card {{ border-top: 6px solid #41B6C4; background: #F7FBFD; border-radius: 6px; padding: 26px; min-height: 430px; display: flex; flex-direction: column; }}
.card p {{ font-size: 24px; margin: 0 0 6px; }} .card em {{ color: #5B6773; font-size: 21px; flex: 1; }} .card h3 {{ font-size: 30px; }}
.card b {{ font-size: 32px; color: #0B3C5D; }}
.note {{ font-size: 22px; color: #3D4A57; margin-top: 26px; line-height: 1.45; }}
.t {{ border-collapse: collapse; width: 100%; font-size: 25px; }}
.t th {{ text-align: left; background: #EDF8FB; color: #0B3C5D; padding: 13px 16px; }}
.t td {{ padding: 13px 16px; border-bottom: 1px solid #E3E9EF; }}
.t tr.sel td {{ font-weight: 700; color: #0B3C5D; background: #F2FAF5; }}
.split {{ display: grid; grid-template-columns: 620px 1fr; gap: 40px; align-items: start; }}
.map {{ width: 100%; max-height: 640px; object-fit: contain; margin-top: -40px; }}
.list {{ font-size: 23px; line-height: 1.5; padding-left: 0; list-style: none; color: #3D4A57; }}
.list li {{ position: relative; padding-left: 28px; margin: 8px 0; }}
.list li::before {{ content: ""; position: absolute; left: 4px; top: 13px; width: 10px; height: 10px; border-radius: 2px; background: #41B6C4; }}
.flow {{ display: flex; align-items: stretch; gap: 14px; }}
.flow div {{ flex: 1; background: #EDF8FB; border-radius: 8px; padding: 30px 24px; min-height: 230px; font-size: 32px; font-weight: 700; color: #0B3C5D; }}
.flow div.dw {{ background: #0B3C5D; color: #fff; }} .flow div.dw span {{ color: #C7E9B4; }}
.flow span {{ display: block; font-size: 20px; font-weight: 400; color: #5B6773; margin-top: 8px; line-height: 1.4; }}
.flow i {{ font-style: normal; font-size: 40px; color: #41B6C4; align-self: center; }}
.wide {{ width: 100%; max-height: 470px; object-fit: contain; }}
.two {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: -20px; }} .two img {{ width: 100%; }}
.bars {{ margin-top: 10px; }}
.bar-row {{ display: grid; grid-template-columns: 600px 1fr 120px; align-items: center; gap: 24px; margin: 44px 0; font-size: 26px; }}
.bar-row b {{ font-size: 38px; color: #0B3C5D; text-align: right; }}
.track {{ position: relative; height: 46px; background: #F2F5F8; border-radius: 4px; }}
.track::after {{ content: ""; position: absolute; left: 50%; top: -6px; bottom: -6px; width: 2px; background: #9AA5B1; }}
.pos {{ position: absolute; left: 50%; top: 0; bottom: 0; background: #225EA8; border-radius: 0 4px 4px 0; }}
.neg {{ position: absolute; right: 50%; top: 0; bottom: 0; background: #41B6C4; border-radius: 4px 0 0 4px; }}
.chart {{ width: 100%; max-height: 250px; object-fit: contain; object-position: left; margin-top: 14px; }}
.callout {{ margin-top: 22px; background: #FFF7EC; border-left: 6px solid #FE9929; border-radius: 6px; padding: 18px 22px; }}
.callout p {{ font-size: 22px; line-height: 1.45; margin: 0; color: #3D4A57; }}
.two-text {{ display: grid; grid-template-columns: 1fr 1fr; gap: 70px; }} .two-text .list {{ font-size: 26px; }} .two-text .list li {{ margin: 18px 0; }} .two-text .list li::before {{ top: 15px; }}
</style></head><body>{''.join(S)}</body></html>"""


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
    print(f"slides written to {PDF_OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
