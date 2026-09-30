"""Shared visual style for maps and figures: light background, blue-green sequential scale."""

from __future__ import annotations

import geopandas as gpd
import mapclassify
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

INK = "#1F2A36"
MUTED = "#5B6773"
BORDER = "#3A3A3A"
NO_DATA = "#E3E6EA"
ACCENT = "#225EA8"
SEQUENTIAL = [mpl.colors.to_hex(mpl.colormaps["YlGnBu"](x)) for x in (0.15, 0.35, 0.55, 0.75, 0.95)]
QUALITATIVE = ["#1D91C0", "#41AB5D", "#FE9929", "#807DBA", "#E7298A", "#8C6D31", "#66C2A4", "#BDBDBD"]
LISA_COLOURS = {"High-High": "#D7301F", "Low-Low": "#2C7FB8", "High-Low": "#FC8D59",
                "Low-High": "#9ECAE1", "Not significant": "#EEEEEE"}
SOURCE_NOTE = "Source: INEGI Census 2020, DENUE and Marco Geoestadístico 2020 · computed in the warehouse"

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "axes.edgecolor": MUTED,
    "axes.labelcolor": INK,
    "xtick.color": MUTED,
    "ytick.color": MUTED,
    "axes.spines.top": False,
    "axes.spines.right": False,
})


def new_map(title: str, subtitle: str = ""):
    fig, ax = plt.subplots(figsize=(7.2, 7.2), dpi=150)
    fig.patch.set_facecolor("white")
    ax.set_axis_off()
    fig.text(0.06, 0.95, title, fontsize=14, fontweight="bold", color=INK, ha="left")
    if subtitle:
        fig.text(0.06, 0.92, subtitle, fontsize=9, color=MUTED, ha="left")
    fig.text(0.06, 0.03, SOURCE_NOTE, fontsize=7, color=MUTED, ha="left")
    return fig, ax


def outline(ax, gdf: gpd.GeoDataFrame) -> None:
    gdf.dissolve().boundary.plot(ax=ax, color=BORDER, linewidth=0.6)


def legend(ax, colours, labels, title: str) -> None:
    handles = [Patch(facecolor=c, edgecolor="none", label=l) for c, l in zip(colours, labels)]
    leg = ax.legend(handles=handles, title=title, loc="upper left", bbox_to_anchor=(1.0, 0.45),
                    frameon=False, fontsize=8, title_fontsize=8.5, labelcolor=INK)
    leg.get_title().set_color(INK)


def choropleth(gdf: gpd.GeoDataFrame, column: str, title: str, unit: str, subtitle: str = "",
               mask=None, mask_label: str = "", k: int = 5, fmt: str = "{:,.0f}"):
    """Quantile choropleth. Rows where `mask` is True, or the value is missing, are drawn
    in grey and listed in the legend with `mask_label`."""
    fig, ax = new_map(title, subtitle)
    excluded = gdf[column].isna()
    if mask is not None:
        excluded = excluded | mask
    data = gdf[~excluded]
    classes = mapclassify.Quantiles(data[column], k=k)
    bins = [data[column].min()] + list(classes.bins)
    labels = [f"{fmt.format(bins[i])} – {fmt.format(bins[i + 1])}" for i in range(len(classes.bins))]
    colours = SEQUENTIAL[:len(labels)] if len(labels) == 5 else [
        mpl.colors.to_hex(mpl.colormaps["YlGnBu"](x)) for x in
        [0.15 + 0.8 * i / max(len(labels) - 1, 1) for i in range(len(labels))]]
    data.plot(ax=ax, color=[colours[c] for c in classes.yb], edgecolor="white", linewidth=0.3)
    if excluded.any():
        gdf[excluded].plot(ax=ax, color=NO_DATA, edgecolor="white", linewidth=0.3)
        colours = colours + [NO_DATA]
        labels = labels + [mask_label or "not available"]
    outline(ax, gdf)
    legend(ax, colours, labels, f"{unit}  (quintiles)")
    return fig, ax


def save(fig, path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, facecolor="white", bbox_inches="tight", pad_inches=0.25)
    plt.close(fig)
