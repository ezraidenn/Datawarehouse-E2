"""Correlation between pairs of AGEB indicators, read from dw.vw_kpi_ageb.

Method: Spearman's rank correlation is the primary measure because densities and rates are
strongly right-skewed and contain extreme AGEBs. Pearson is reported on log(1 + x) values as a
check of a linear relationship on the transformed scale. AGEBs with fewer than 100 residents
are excluded from every pair that involves a per-capita indicator.

Outputs: outputs/correlations.csv and one scatter plot per pair in outputs/figures/.

Usage: python -m src.analysis.correlations
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

from src import config
from src.analysis import style
from src.analysis.dw_io import crime_loaded, read_from_dw

PER_CAPITA = {"businesses_per_1000", "crime_rate_per_1000", "pea_rate_pct",
              "share_0_14_pct", "share_15_64_pct", "share_65_plus_pct"}

LABELS = {
    "pop_density_km2": "Population density (inhabitants per km²)",
    "business_density_km2": "Business density (establishments per km²)",
    "retail_density_km2": "Retail density (per km²)",
    "service_density_km2": "Service density (per km²)",
    "pea_rate_pct": "Economically active population rate (%)",
    "share_65_plus_pct": "Population aged 65+ (%)",
    "businesses_per_1000": "Businesses per 1,000 residents",
    "crime_rate_per_1000": "Crime rate (per 1,000 residents)",
    "crimes_total": "Crime incidents",
}

PAIRS = [
    ("pop_density_km2", "business_density_km2"),
    ("pop_density_km2", "businesses_per_1000"),
    ("pea_rate_pct", "businesses_per_1000"),
    ("share_65_plus_pct", "service_density_km2"),
]
CRIME_PAIRS = [
    ("business_density_km2", "crime_rate_per_1000"),
    ("pop_density_km2", "crime_rate_per_1000"),
    ("business_density_km2", "crimes_total"),
]


def analyse(kpi: pd.DataFrame, x: str, y: str) -> tuple[dict, pd.DataFrame]:
    data = kpi[["cvegeo", x, y, "low_population"]].dropna(subset=[x, y])
    if {x, y} & PER_CAPITA:
        data = data[~data["low_population"]]
    rho, p_rho = stats.spearmanr(data[x], data[y])
    r, p_r = stats.pearsonr(np.log1p(data[x].astype(float)), np.log1p(data[y].astype(float)))
    return {
        "x": x, "y": y, "n": len(data),
        "spearman_rho": round(float(rho), 4), "spearman_p": float(p_rho),
        "pearson_r_log": round(float(r), 4), "pearson_p_log": float(p_r),
        "excluded_low_population": bool({x, y} & PER_CAPITA),
    }, data


def scatter(data: pd.DataFrame, result: dict, path) -> None:
    x, y = result["x"], result["y"]
    fig, ax = plt.subplots(figsize=(6.4, 4.8), dpi=150)
    ax.scatter(data[x], data[y], s=12, color=style.SEQUENTIAL[3], alpha=0.55, edgecolor="none")
    ax.set_xscale("symlog", linthresh=1)
    ax.set_yscale("symlog", linthresh=1)
    ax.set_xlabel(LABELS.get(x, x) + "  (log scale)", fontsize=9)
    ax.set_ylabel(LABELS.get(y, y) + "  (log scale)", fontsize=9)
    ax.set_title(f"Spearman ρ = {result['spearman_rho']:.2f}  ·  p = {result['spearman_p']:.2g}  ·  "
                 f"n = {result['n']}", fontsize=9, color=style.MUTED, loc="left")
    fig.suptitle(f"{LABELS.get(y, y)}\nvs {LABELS.get(x, x).lower()}", fontsize=11,
                 fontweight="bold", color=style.INK, x=0.02, ha="left", y=1.03)
    ax.grid(alpha=0.25)
    style.save(fig, path)


def main() -> None:
    kpi = read_from_dw("vw_kpi_ageb")
    pairs = PAIRS + (CRIME_PAIRS if crime_loaded() else [])
    results = []
    for i, (x, y) in enumerate(pairs, start=1):
        result, data = analyse(kpi, x, y)
        results.append(result)
        scatter(data, result, config.FIGURES / f"corr_{i:02d}_{x}__{y}.png")
    table = pd.DataFrame(results)
    table.to_csv(config.OUTPUTS / "correlations.csv", index=False)
    print(table.to_string(index=False))


if __name__ == "__main__":
    main()
