"""Choropleth maps of selected KPIs, read from dw.vw_kpi_ageb_geo.

Usage: python -m src.analysis.kpi_maps
"""

from __future__ import annotations

from src import config
from src.analysis import style
from src.analysis.dw_io import crime_loaded, read_from_dw

LOW_POP = "fewer than 100 residents"


def main() -> None:
    gdf = read_from_dw("vw_kpi_ageb_geo", geometry=True)
    out = config.MAPS

    maps = [
        ("pop_density_km2", "Population density", "Inhabitants per km²", None, "", "{:,.0f}", "01_population_density.png"),
        ("pea_rate_pct", "Economically active population rate", "% of population aged 12+", None, "", "{:.1f}", "02_pea_rate.png"),
        ("share_65_plus_pct", "Population aged 65 and over", "% of residents", None, "", "{:.1f}", "03_share_65_plus.png"),
        ("business_density_km2", "Business density", "Establishments per km²", None, "", "{:,.0f}", "04_business_density.png"),
        ("retail_density_km2", "Retail density", "Retail establishments per km²", None, "", "{:,.0f}", "05_retail_density.png"),
        ("service_density_km2", "Service density", "Service establishments per km²", None, "", "{:,.0f}", "06_service_density.png"),
        ("businesses_per_1000", "Businesses per 1,000 residents", "Establishments per 1,000 residents",
         gdf["low_population"].fillna(True), LOW_POP, "{:,.0f}", "07_businesses_per_1000.png"),
    ]
    if crime_loaded():
        maps += [
            ("crimes_total", "Crime incidents", "Incidents", None, "", "{:,.0f}", "09_crime_incidents.png"),
            ("crime_rate_per_1000", "Crime rate", "Incidents per 1,000 residents",
             gdf["low_population"].fillna(True), LOW_POP, "{:,.1f}", "10_crime_rate.png"),
            ("crimes_per_100_businesses", "Crime relative to business activity", "Incidents per 100 establishments",
             None, "no establishments", "{:,.1f}", "11_crime_per_100_businesses.png"),
        ]

    for column, title, unit, mask, mask_label, fmt, name in maps:
        fig, _ = style.choropleth(gdf, column, title, unit, subtitle="Urban AGEBs of Mérida",
                                  mask=mask, mask_label=mask_label, fmt=fmt)
        style.save(fig, out / name)

    # Dominant economic activity (categorical)
    fig, ax = style.new_map("Dominant economic activity", "Sector with the most establishments in each AGEB")
    counts = gdf["dominant_sector"].value_counts()
    top = list(counts.index[:7])
    category = gdf["dominant_sector"].where(gdf["dominant_sector"].isin(top), "Other sectors")
    category = category.where(gdf["dominant_sector"].notna(), "No establishments")
    order = top + ["Other sectors", "No establishments"]
    colours = dict(zip(order, style.QUALITATIVE[:len(top)] + ["#BDBDBD", style.NO_DATA]))
    gdf.plot(ax=ax, color=[colours[c] for c in category], edgecolor="white", linewidth=0.3)
    style.outline(ax, gdf)
    present = [c for c in order if (category == c).any()]
    style.legend(ax, [colours[c] for c in present],
                 [f"{c} ({int((category == c).sum())})" for c in present], "Sector (number of AGEBs)")
    style.save(fig, out / "08_dominant_activity.png")

    print(f"maps written to {out.relative_to(config.ROOT)}: {len(maps) + 1}")


if __name__ == "__main__":
    main()
