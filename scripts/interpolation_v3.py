import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import geodatasets
from matplotlib.colors import LogNorm, ListedColormap
import numpy as np
from scipy.interpolate import Rbf

import rasterio
from rasterio.enums import Resampling
from rasterio.vrt import WarpedVRT

# ---------------------------------------------------------
# 1) Tambora-Daten laden
# ---------------------------------------------------------
df = pd.read_csv("tambora_ashfall.csv")

df["Thickness_cm_clean"] = (
    df["Thickness_cm"]
    .astype(str)
    .str.extract(r"([\d.]+)")
    .astype(float)
    .fillna(0)
)

gdf = gpd.GeoDataFrame(
    df,
    geometry=gpd.points_from_xy(df["Longitude"], df["Latitude"]),
    crs="EPSG:4326"
)

# ---------------------------------------------------------
# 2) Basis-Weltkarte
# ---------------------------------------------------------
world = gpd.read_file(geodatasets.get_path("naturalearth.land"))

fig, ax = plt.subplots(figsize=(12, 6))

# gefüllte Weltkarte
world.plot(ax=ax, color="#dddddd", edgecolor="#555555", linewidth=0.5)

# ---------------------------------------------------------
# 3) Agriculture-Map (indo_agri_map.tif) über den GANZEN Bereich
# ---------------------------------------------------------

with rasterio.open("indo_agri_map.tif") as src:
    if src.crs is None:
        raise RuntimeError("indo_agri_map.tif hat kein CRS – bitte prüfen.")

    # alles am Ende in EPSG:4326
    if src.crs.to_string() != "EPSG:4326":
        with WarpedVRT(src, crs="EPSG:4326") as vrt:
            width, height = vrt.width, vrt.height

            max_size = 2000  # max. Pixel pro Dimension
            scale = max(width / max_size, height / max_size, 1)
            out_w = int(width / scale)
            out_h = int(height / scale)

            lulc = vrt.read(
                1,
                out_shape=(out_h, out_w),
                resampling=Resampling.nearest,
                out_dtype="uint8",
            )
            bounds = vrt.bounds
    else:
        width, height = src.width, src.height
        max_size = 2000
        scale = max(width / max_size, height / max_size, 1)
        out_w = int(width / scale)
        out_h = int(height / max_size) if height / max_size > width / max_size else int(height / scale)

        lulc = src.read(
            1,
            out_shape=(out_h, out_w),
            resampling=Resampling.nearest,
            out_dtype="uint8",
        )
        bounds = src.bounds

# Extent des Rasters (jetzt in lon/lat)
extent = (bounds.left, bounds.right, bounds.bottom, bounds.top)

# ---------------------------------------------------------
# 3) Klassen-Colormap für LULC
# ---------------------------------------------------------
# 0 interpretieren wir als "NoData" → transparent
# alle anderen Klassen bekommen Farben
vals = np.unique(lulc)
vals = vals[vals != 0]  # 0 als Hintergrund

# einfache automatische Farbpalette (du kannst später für jede Klasse explizit Farben vergeben)
# z.B. forest, water etc. nach Legende
base_colors = plt.cm.tab20(np.linspace(0, 1, len(vals)))
# Colormap-Array mit Index=max(vals)+1
cmap_arr = np.zeros((int(vals.max()) + 1, 4))
cmap_arr[0] = (0, 0, 0, 0)  # 0 = transparent
for i, v in enumerate(vals):
    cmap_arr[int(v)] = base_colors[i]

lulc_cmap = ListedColormap(cmap_arr)

# ---------------------------------------------------------
# 4) LULC-Raster zeichnen (ALLE Klassen sichtbar)
# ---------------------------------------------------------
ax.imshow(
    lulc,
    cmap=lulc_cmap,
    extent=extent,
    origin="upper",
    zorder=1   # liegt über Weltumriss
)

# Welt-Achsen: gesamte Welt anzeigen
minx, miny, maxx, maxy = world.total_bounds
ax.set_xlim(minx, maxx)
ax.set_ylim(miny, maxy)

# ---------------------------------------------------------
# 4) Asche-Interpolation NUR um Tambora herum
# ---------------------------------------------------------
lon_min, lon_max = gdf["Longitude"].min(), gdf["Longitude"].max()
lat_min, lat_max = gdf["Latitude"].min(), gdf["Latitude"].max()
lon_pad = 0.9 * (lon_max - lon_min)
lat_pad = 0.9 * (lat_max - lat_min)

xmin = lon_min - lon_pad
xmax = lon_max + lon_pad
ymin = lat_min - lat_pad
ymax = lat_max + lat_pad

mask_pos = gdf["Thickness_cm_clean"] > 0
x = gdf.loc[mask_pos, "Longitude"].values
y = gdf.loc[mask_pos, "Latitude"].values
z = gdf.loc[mask_pos, "Thickness_cm_clean"].values

if len(z) < 5:
    raise RuntimeError("Zu wenige valide Messpunkte für eine sinnvolle Interpolation.")

nx, ny = 300, 300
xi = np.linspace(xmin, xmax, nx)
yi = np.linspace(ymin, ymax, ny)
XI, YI = np.meshgrid(xi, yi)

eps = 1e-2
z_log = np.log10(z + eps)

rbf = Rbf(x, y, z_log, function="multiquadric", smooth=0.005)
ZI_log = rbf(XI, YI)
ZI = (10**ZI_log) - eps
ZI[ZI <= 0] = np.nan

vmin = max(np.nanmin(ZI[ZI > 0]), 0.05)
vmax = np.nanmax(ZI)
norm = LogNorm(vmin=vmin, vmax=vmax)

im = ax.pcolormesh(
    XI, YI, ZI,
    shading="auto",
    cmap="inferno",
    norm=norm,
    alpha=0.55,
    zorder=2.0
)

# Messpunkte > 0
ax.scatter(
    x, y,
    c=z,
    cmap="inferno",
    norm=norm,
    s=40,
    edgecolor="#555555",
    linewidth=0.5,
    zorder=2,
    label="Measurements > 0"
)

# Messpunkte = 0
zero_mask = gdf["Thickness_cm_clean"] == 0
x0 = gdf.loc[zero_mask, "Longitude"].values
y0 = gdf.loc[zero_mask, "Latitude"].values

ax.scatter(
    x0, y0,
    s=35,
    c="#4aa3ff",
    edgecolor="#333333",
    linewidth=0.4,
    zorder=3,
    label="Measurements = 0"
)

# ---------------------------------------------------------
# 5) Achsen auf WELT setzen & Layout
# ---------------------------------------------------------
# Welt-Ausdehnung aus dem NaturalEarth-Shape
minx, miny, maxx, maxy = world.total_bounds
ax.set_xlim(minx, maxx)
ax.set_ylim(miny, maxy)

cbar = plt.colorbar(im, ax=ax, shrink=0.85)
cbar.set_label("Ash thickness [cm] (log scale)")
ticks = np.array([0.1, 0.3, 1, 3, 10, 30, 100])
ticks = ticks[(ticks >= vmin) & (ticks <= vmax)]
cbar.set_ticks(ticks)
cbar.set_ticklabels([str(t) for t in ticks])

ax.set_title("Ash Fall Measurements (Tambora 1815) + Agriculture", fontsize=14)
ax.set_xlabel("Longitude")
ax.set_ylabel("Latitude")
ax.legend(loc="upper right")

plt.tight_layout()
plt.show()


