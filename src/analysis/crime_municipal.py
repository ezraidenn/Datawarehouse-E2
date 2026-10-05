"""Municipal public safety: crime KPIs 11-14 at municipal level, from the warehouse.

The SESNSP counts carry no location, so they describe Mérida as a whole. This module reports
the reference year (the latest year with twelve months of data), the monthly series by crime
group (KPI 13, time) and the crime types of the reference year (KPI 13, type).

Outputs: outputs/crime_municipal_summary.json, outputs/crime_municipal_year.csv,
outputs/figures/crime_municipal_trend.png, outputs/figures/crime_municipal_types.png

Usage: python -m src.analysis.crime_municipal
"""

from __future__ import annotations

import json

import matplotlib.pyplot as plt
import pandas as pd

from src import config
from src.analysis import style
from src.analysis.dw_io import read_from_dw

GROUP_COLOURS = {
    "Property": "#225EA8", "Family": "#41B6C4", "Life and bodily integrity": "#EF6548",
    "Sexual freedom and safety": "#807DBA", "Society": "#FE9929", "Personal liberty": "#8C6D31",
    "Other": "#BDBDBD",
}


def main() -> None:
    yearly = read_from_dw("vw_kpi_crime_municipal_year").sort_values("year")
    if yearly.empty:
        print("municipal crime: no data loaded")
        return
    monthly = read_from_dw("vw_crime_municipal_month")
    yearly.to_csv(config.OUTPUTS / "crime_municipal_year.csv", index=False)

    ref = yearly[yearly["months_reported"] == 12].iloc[-1]
    year = int(ref["year"])
    in_year = monthly[monthly["year"] == year]
    by_group = in_year.groupby("crime_group")["incidents"].sum().sort_values(ascending=False)
    by_category = in_year.groupby("crime_category")["incidents"].sum().sort_values(ascending=False)
    top_specific = by_group.drop(labels="Other", errors="ignore")

    summary = {
        "year": year,
        "incidents_year": int(ref["crimes_total"]),
        "rate_per_1000": float(ref["crime_rate_per_1000"]),
        "per_100_businesses": float(ref["crimes_per_100_businesses"]),
        "top_type": f"{top_specific.index[0]} crimes",
        "top_type_share": float(100 * top_specific.iloc[0] / by_group.sum()),
        "top_category": by_category.index[0],
        "top_category_share": float(100 * by_category.iloc[0] / by_category.sum()),
        "rows": int(len(monthly)),
        "years": [int(yearly["year"].min()), int(yearly["year"].max())],
        "series": {int(r.year): int(r.crimes_total) for r in yearly.itertuples()},
    }
    (config.OUTPUTS / "crime_municipal_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    # Monthly series by crime group (stacked)
    series = (monthly.assign(period=pd.to_datetime(dict(year=monthly["year"], month=monthly["month"], day=1)))
              .pivot_table(index="period", columns="crime_group", values="incidents", aggfunc="sum")
              .fillna(0))
    order = [g for g in GROUP_COLOURS if g in series.columns]
    fig, ax = plt.subplots(figsize=(10, 4.6), dpi=150)
    ax.stackplot(series.index, [series[g] for g in order], labels=order,
                 colors=[GROUP_COLOURS[g] for g in order], alpha=0.9, linewidth=0)
    ax.set_ylabel("Incidents per month", fontsize=9)
    ax.grid(axis="y", alpha=0.25)
    ax.legend(loc="upper right", fontsize=7.5, frameon=False, ncol=2)
    fig.suptitle("Monthly crime incidents in the municipality of Mérida, by legal good affected",
                 fontsize=11, fontweight="bold", color=style.INK, x=0.02, ha="left")
    ax.set_title("SESNSP common-jurisdiction incidence · abrupt breaks in mid-2017 and mid-2021 suggest changes "
                 "in recording, so long-term trends are not interpreted", fontsize=8, color=style.MUTED, loc="left")
    style.save(fig, config.FIGURES / "crime_municipal_trend.png")

    # Crime types of the reference year
    top = by_category.head(10).sort_values()
    groups = in_year.groupby("crime_category")["crime_group"].first()
    fig, ax = plt.subplots(figsize=(8.5, 4.6), dpi=150)
    ax.barh(top.index, top.values, color=[GROUP_COLOURS.get(groups[c], "#BDBDBD") for c in top.index])
    for i, v in enumerate(top.values):
        ax.text(v, i, f" {v:,}", va="center", fontsize=8, color=style.INK)
    ax.set_xlabel(f"Incidents in {year}", fontsize=9)
    ax.tick_params(axis="y", labelsize=8)
    fig.suptitle(f"Most frequent crime types in Mérida, {year}", fontsize=11, fontweight="bold",
                 color=style.INK, x=0.02, ha="left")
    ax.set_title("SESNSP category names as published; colour = legal good affected", fontsize=8,
                 color=style.MUTED, loc="left")
    style.save(fig, config.FIGURES / "crime_municipal_types.png")

    print(json.dumps({k: v for k, v in summary.items() if k != "series"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
