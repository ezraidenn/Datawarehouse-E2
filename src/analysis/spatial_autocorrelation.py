"""Global, local and bivariate spatial autocorrelation of AGEB indicators.

Neighbourhood rule: Queen contiguity (two AGEBs are neighbours when they share an edge or a
vertex), row-standardised, so the spatial lag of an AGEB is the mean of its neighbours.
Inference: 999 random permutations, fixed seed, pseudo p-values; significance level 0.05.
Values: log(1 + x) of each indicator, because densities are strongly right-skewed.
AGEBs with a missing value, and those with fewer than 100 residents for per-capita indicators,
are removed before the weights are built; AGEBs left without neighbours (islands) are
reported and excluded.

Outputs: outputs/moran_results.csv, outputs/lisa_clusters.csv, LISA maps in outputs/maps/.

Usage: python -m src.analysis.spatial_autocorrelation
"""

from __future__ import annotations

import warnings

import geopandas as gpd
import numpy as np
import pandas as pd
from esda.moran import Moran, Moran_BV, Moran_Local, Moran_Local_BV
from libpysal.weights import Queen

from src import config
from src.analysis import style
from src.analysis.dw_io import crime_loaded, read_from_dw

PERMUTATIONS = 999
SEED = 20261005
ALPHA = 0.05
PER_CAPITA = {"businesses_per_1000", "crime_rate_per_1000", "pea_rate_pct", "share_65_plus_pct"}

GLOBAL = ["pop_density_km2", "business_density_km2", "pea_rate_pct", "businesses_per_1000"]
LOCAL = ["pop_density_km2", "business_density_km2"]
BIVARIATE = [("business_density_km2", "pop_density_km2")]
CRIME_GLOBAL = ["crime_rate_per_1000"]
CRIME_LOCAL = ["crime_rate_per_1000"]
CRIME_BIVARIATE = [("business_density_km2", "crime_rate_per_1000")]

TITLES = {
    "pop_density_km2": "population density",
    "business_density_km2": "business density",
    "pea_rate_pct": "economically active population rate",
    "businesses_per_1000": "businesses per 1,000 residents",
    "crime_rate_per_1000": "crime rate",
}
QUADRANT = {1: "High-High", 2: "Low-High", 3: "Low-Low", 4: "High-Low"}


def prepare(gdf: gpd.GeoDataFrame, columns: list[str]):
    """Rows usable for the given columns and their Queen weights without islands."""
    data = gdf.dropna(subset=columns)
    if set(columns) & PER_CAPITA:
        data = data[~data["low_population"]]
    data = data.reset_index(drop=True)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        w = Queen.from_dataframe(data, use_index=False)
    islands = list(w.islands)
    if islands:
        data = data.drop(index=islands).reset_index(drop=True)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            w = Queen.from_dataframe(data, use_index=False)
    w.transform = "r"
    return data, w, len(islands)


def values(data: pd.DataFrame, column: str) -> np.ndarray:
    return np.log1p(data[column].astype(float).to_numpy())


def lisa_labels(local, significant: np.ndarray) -> np.ndarray:
    labels = np.array([QUADRANT[q] for q in local.q], dtype=object)
    labels[~significant] = "Not significant"
    return labels


def lisa_map(data: gpd.GeoDataFrame, labels: np.ndarray, title: str, subtitle: str, path) -> None:
    fig, ax = style.new_map(title, subtitle)
    colours = [style.LISA_COLOURS[l] for l in labels]
    data.plot(ax=ax, color=colours, edgecolor="white", linewidth=0.3)
    style.outline(ax, data)
    order = ["High-High", "Low-Low", "High-Low", "Low-High", "Not significant"]
    style.legend(ax, [style.LISA_COLOURS[o] for o in order],
                 [f"{o} ({int((labels == o).sum())})" for o in order],
                 f"LISA, p < {ALPHA}, {PERMUTATIONS} permutations")
    style.save(fig, path)


def main() -> None:
    np.random.seed(SEED)
    gdf = read_from_dw("vw_kpi_ageb_geo", geometry=True)
    with_crime = crime_loaded()
    global_vars = GLOBAL + (CRIME_GLOBAL if with_crime else [])
    local_vars = LOCAL + (CRIME_LOCAL if with_crime else [])
    bivariate = BIVARIATE + (CRIME_BIVARIATE if with_crime else [])

    rows, clusters = [], []

    for column in global_vars:
        data, w, islands = prepare(gdf, [column])
        mi = Moran(values(data, column), w, permutations=PERMUTATIONS)
        rows.append({"analysis": "global Moran's I", "x": column, "y": "", "n": len(data),
                     "islands_excluded": islands, "statistic": round(mi.I, 4),
                     "expected": round(mi.EI, 4), "z_sim": round(mi.z_sim, 3), "p_sim": mi.p_sim})

    for i, column in enumerate(local_vars, start=1):
        data, w, islands = prepare(gdf, [column])
        local = Moran_Local(values(data, column), w, permutations=PERMUTATIONS, seed=SEED)
        labels = lisa_labels(local, local.p_sim < ALPHA)
        lisa_map(data, labels, f"Local clusters of {TITLES[column]}",
                 "Local Moran's I (LISA), Queen contiguity, log values",
                 config.MAPS / f"lisa_{i:02d}_{column}.png")
        clusters.append(pd.DataFrame({"analysis": "LISA", "x": column, "y": "",
                                      "cvegeo": data["cvegeo"], "cluster": labels,
                                      "local_i": local.Is, "p_sim": local.p_sim}))
        counts = pd.Series(labels).value_counts().to_dict()
        rows.append({"analysis": "LISA", "x": column, "y": "", "n": len(data), "islands_excluded": islands,
                     **{f"n_{k.lower().replace('-', '_').replace(' ', '_')}": v for k, v in counts.items()}})

    for j, (x, y) in enumerate(bivariate, start=1):
        data, w, islands = prepare(gdf, [x, y])
        bv = Moran_BV(values(data, x), values(data, y), w, permutations=PERMUTATIONS)
        rows.append({"analysis": "bivariate Moran's I", "x": x, "y": y, "n": len(data),
                     "islands_excluded": islands, "statistic": round(bv.I, 4),
                     "z_sim": round(bv.z_sim, 3), "p_sim": bv.p_sim})
        local = Moran_Local_BV(values(data, x), values(data, y), w, permutations=PERMUTATIONS, seed=SEED)
        labels = lisa_labels(local, local.p_sim < ALPHA)
        lisa_map(data, labels, f"{TITLES[x].capitalize()} vs neighbouring {TITLES[y]}",
                 "Bivariate LISA: value of x in the AGEB against the mean of y in its neighbours",
                 config.MAPS / f"bilisa_{j:02d}_{x}__{y}.png")
        clusters.append(pd.DataFrame({"analysis": "bivariate LISA", "x": x, "y": y,
                                      "cvegeo": data["cvegeo"], "cluster": labels,
                                      "local_i": local.Is, "p_sim": local.p_sim}))

    results = pd.DataFrame(rows)
    results.to_csv(config.OUTPUTS / "moran_results.csv", index=False)
    pd.concat(clusters, ignore_index=True).to_csv(config.OUTPUTS / "lisa_clusters.csv", index=False)
    print(results.to_string(index=False))


if __name__ == "__main__":
    main()
