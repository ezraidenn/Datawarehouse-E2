# Glossary

Terms used in the README, the notebooks and the technical report.

| Term | Meaning |
|---|---|
| AGEB | Área Geoestadística Básica, the basic geostatistical unit used for the study. In Mérida, AGEBs are the urban areas for which INEGI publishes census and polygon data. |
| CVEGEO | The official INEGI geostatistical code that uniquely identifies a unit such as state, municipality, locality and AGEB within the national hierarchy. |
| Marco Geoestadístico | INEGI’s official geostatistical framework, used to define the boundaries and codes of local administrative and statistical areas. |
| DENUE | National Statistical Directory of Economic Units, the business register published by INEGI with one record per establishment and its coordinates. |
| SCIAN | Mexico’s economic activity classification system, which organises establishments by industry and sector. |
| Economically active population (PEA) | The part of the population aged 12 and over who is working or actively seeking work, used to compute activity rates. |
| Grain | The level of detail represented by one row in a table or view. For example, one AGEB or one business. |
| Fact table | A table containing measurable events or metrics, usually with a clear grain and foreign keys to dimensions. |
| Dimension table | A descriptive table that provides context for fact rows, such as geography, dates, activity codes or data sources. |
| Constellation schema | A warehouse design with multiple fact tables that share several dimensions, instead of a single central fact table. |
| Staging | An intermediate schema where raw or cleaned data is loaded before validation and warehouse population. |
| CRS | Coordinate Reference System, the framework used to define the positions of spatial data on the Earth’s surface. |
| EPSG:4326 | The WGS 84 geographic CRS based on latitude and longitude, used by point sources such as DENUE and crime locations. |
| EPSG:6372 | The official Mexico ITRF2008 / LCC projection used for area measurement and geostatistical work in this project. |
| Spatial join | The process of assigning points to the polygon that contains them, such as placing businesses inside an AGEB. |
| Quantile classification | A choropleth method that divides a variable into classes with roughly equal numbers of observations, used to compare areas. |
| Spearman correlation | A rank-based correlation coefficient used when relationships are monotonic but not necessarily linear or normally distributed. |
| Pearson correlation | A linear correlation coefficient that measures the strength of a straight-line relationship between two continuous variables. |
| Spatial autocorrelation | The degree to which nearby areas have similar values, measured with local and global statistical tests. |
| Moran’s I | A global measure of spatial autocorrelation that indicates whether values cluster, disperse or are randomly arranged across space. |
| LISA | Local Indicators of Spatial Association, a local statistic that identifies clusters and outliers in specific neighbourhoods. |
| High-High / Low-Low / High-Low / Low-High | Local Moran categories describing whether a location and its neighbours are both high, both low, or mixed in opposite directions. |
| Bivariate Moran’s I | A spatial autocorrelation metric used to assess the joint relationship between two variables across neighbouring areas. |
| Queen contiguity | A neighbour rule in which polygons are connected if they share a border or a vertex. |
| Row-standardised weights | A spatial weights matrix in which each row is normalised to sum to one, commonly used before computing local or global spatial statistics. |
| Permutation p-value | A significance value obtained by repeatedly shuffling the data to estimate how unusual the observed statistic would be under randomness. |
| Modifiable areal unit problem (MAUP) | The fact that statistical results can change when the same data are aggregated into different boundary systems. |
| Ecological fallacy | The error of assuming that patterns observed at the area level also apply to every person or household within that area. |
