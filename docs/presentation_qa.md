# Presentation Q&A

### Q: Why the urban AGEB and not blocks or colonias?
Blocks are too small: the median block has 52 people and a third of them contain no business. Colonias are not published by INEGI as official polygons or census results. The urban AGEB has official polygons, one-to-one census keys and 526 units, enough for spatial statistics.

### Q: Why is crime not analysed by AGEB?
The public-safety source for Mérida is published only as municipal counts without coordinates. The project therefore reports crime at municipal level and never assigns counts to AGEBs. AGEB crime KPIs remain NULL until a georeferenced source exists.

### Q: How do you know the spatial join is correct?
Every DENUE point is assigned to the AGEB polygon that contains it. 99.57% of establishments are assigned to an urban AGEB, and 99.82% of those match the AGEB declared by INEGI. The independent key declared by DENUE confirms the spatial join.

### Q: What happens with census values withheld for confidentiality?
Withheld values are stored as `NULL`, never as zero, and flagged with `has_suppressed`. The project excludes them from rates and reports the affected AGEB as unavailable when needed. At AGEB level, the share of suppressed values is low enough to keep the analysis useful.

### Q: Why are AGEBs with fewer than 100 residents excluded from per-capita indicators?
Very small AGEBs produce unstable ratios and extreme values when divided by a tiny denominator. The project flags 32 AGEBs with fewer than 100 residents and excludes them from per-capita statistics. This avoids misleading comparisons driven by a few residents or businesses.

### Q: Why Spearman instead of Pearson?
The project uses Spearman as the primary measure because densities are highly skewed and contain extreme values. Pearson is used only as a secondary check on log-transformed values. This makes the results more robust to outliers and nonlinear patterns.

### Q: What neighbourhood rule did you use and what does it imply?
The project uses Queen contiguity, where AGEBs are neighbours if they touch by edge or vertex. Only touching AGEBs influence each other, so areas separated by a road reserve are ignored. This is the rule used for Moran’s I and local spatial clusters.

### Q: Does a significant Moran's I mean that one variable causes the other?
No. A significant Moran’s I only tells us that neighbouring areas are similar or dissimilar in space. It indicates clustering, not causation. Association is not the same as a causal effect.

### Q: How can someone reproduce the project from zero?
The README gives a full sequence: clone the repository, create a virtual environment, install dependencies and start PostgreSQL with Docker. Then run `python -m src.download` and `python -m src.run_pipeline` to rebuild the warehouse and KPIs. Optional analysis and report steps follow the same pattern.

### Q: What would you improve with more time or data?
With more time, the project would add a georeferenced crime source and extend the analysis to more recent years. It would also test alternative boundary effects and compare the current AGEB-based results with other neighbourhood definitions. The README clearly notes that crime remains municipal until coordinates become available.
