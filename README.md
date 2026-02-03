# Klima - Proejekt zur Wunderling VL

## Struktur des Projekts & Git
Tambora Ashfall – LULC Overlay & Impact Statistics
=================================================

1. Purpose
----------
This project provides a reproducible workflow to:
  (1) load point-based ashfall thickness measurements (Tambora eruption),
  (2) interpolate ash thickness spatially to a continuous field,
  (3) combine the resulting ash-affected region with a land-use/land-cover raster (LULC),
  (4) compute and print statistics of affected LULC classes,
  (5) identify affected countries and estimate affected land area per country.

The main output is a global visualization (map) and several quantitative summaries
printed to the console.


2. Data
-------------
Main file: tambora_int_data.py
The script expects the following input files:

(A) tambora_ashfall.csv
    Required columns:
      - Longitude
      - Latitude
      - Thickness_cm

    Notes:
      - Thickness_cm may contain strings or units (e.g., "12 cm").
        The code extracts the numeric part and stores it as Thickness_cm_clean.

(B) indo_agri_map.tif
    Raster file containing land-use/land-cover categories.
    - Pixel values are class codes.
    - The script treats 0 as background/NoData.
    - CRS must be defined. If CRS is not EPSG:4326, the script warps to EPSG:4326
      on the fly using rasterio.WarpedVRT.

(C) ne_110m_admin_0_countries.shp (Natural Earth countries)
    Shapefile with country polygons used to determine affected countries.
    Important:
      - Ensure all companion files are present (.dbf, .shx, .prj, ...).
      - The script converts it to EPSG:4326.

Additionally, the script loads a base land layer using:
  - geodatasets.get_path("naturalearth.land")


3. Workflow Summary
-------------------
Step 1: Load country boundaries (EPSG:4326)
Step 2: Load ashfall point data, clean thickness values, create GeoDataFrame
Step 3: Load and downsample LULC raster; ensure EPSG:4326; plot as map overlay
Step 4: Interpolate ash thickness using RBF (log10 transform)
Step 5: Apply an anisotropic taper function (faster decay south of Tambora)
Step 6: Plot ash field + measurement points
Step 7: Build a polygon mask from the ash field above a threshold
Step 8: Rasterize the ash polygon to the LULC raster grid
Step 9: Compute LULC statistics within the ash-affected region
Step 10: Compute affected country areas (intersection country polygons with ash polygon)
Step 11: Print results and render final map with legends


4. Outputs
----------
(A) Visualization:
  - Global map with:
      - land base map
      - LULC raster overlay (colored per class)
      - interpolated ash thickness overlay (log scale)
      - measurement points (positive vs. zero values)
      - LULC legend

(B) Console output:
  - table of LULC classes affected by ash above threshold
  - list of affected countries
  - affected area per country (km^2, equal-area projection)
  - rough LULC-area breakdown for Indonesia


5. Parameters / Key Settings
----------------------------
The script contains several key parameters:

- RBF interpolation:
    function="linear"
    smooth=0.005

- interpolation grid resolution:
    nx=600, ny=600

- taper / cutoff:
    r0=3.5 deg (inner core)
    r1=20.0 deg (outer cutoff)
    south_boost=1.4 

- ash threshold for mask generation:
    threshold = 0.1 (cm)

Note:
  The script contains two different variables called "threshold_calc" and "threshold_plot":
    - one for visualization masking (threshold_plot = x)
    - one for polygon/mask generation (threshold_calc = x)
  This is intentional in the original code and should not be mixed up.


6. Dependencies
---------------
Required Python packages include:
  - numpy
  - pandas
  - matplotlib
  - geopandas
  - shapely
  - scipy
  - rasterio
  - geodatasets


7. Notes / Limitations
----------------------
- The interpolation is performed in geographic coordinates (degrees). This is not a
  true metric distance. For global-scale physics-based modelling one would typically
  use a projected CRS or geodesic distances. Here, degree-based distances are used
  for a pragmatic visualization/statistics workflow.

- The anisotropic taper and outer cutoff are modelling choices to suppress
  unrealistically large influence of the interpolation far away from Tambora.

- LULC statistics are based on pixel counts on a resampled raster grid.
  Absolute area results depend on resolution and projection choices.


## Struktur Versionshistorie


## Indonesia interactive stellite map
https://platform.indonesia.mapbiomas.org/coverage/coverage_lclu?t[regionKey]=indonesia&t[ids][]=4-1-1&t[divisionCategoryId]=2&tl[id]=1&tl[themeKey]=coverage&tl[subthemeKey]=coverage_lclu&tl[pixelValues][]=40&tl[pixelValues][]=35&tl[pixelValues][]=9&tl[pixelValues][]=21&tl[pixelValues][]=30&tl[pixelValues][]=24&tl[pixelValues][]=25&tl[pixelValues][]=3&tl[pixelValues][]=5&tl[pixelValues][]=76&tl[pixelValues][]=27&tl[pixelValues][]=13&tl[pixelValues][]=31&tl[pixelValues][]=33&tl[legendKey]=default&tl[year]=2024

https://registry.opendata.aws/esa-worldcover-vito/?utm_source=chatgpt.com


Es lässt sich eine Tiff bzw .tif Datei herunterladen, die sehr groß ist. Diese ist aber nicht mit normalen Means auszulesen - nicht verwunderlich.
Upload der Datei steht aus.
Genutzte Parameter waren (a) Indonesien, (b) Coverage, (c) 2024 und nicht mehr, meine ich.
