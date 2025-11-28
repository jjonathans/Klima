import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import geodatasets
from matplotlib.colors import LogNorm, LinearSegmentedColormap,ListedColormap, to_rgba
import scipy as sp
import numpy as np
from scipy.interpolate import Rbf, griddata

# CSV laden
df = pd.read_csv("tambora_ashfall.csv")

# Reine Zahlen extrahieren (nicht numerische entfernen)
df["Thickness_cm_clean"] = (
    df["Thickness_cm"]
    .astype(str)
    .str.extract(r"([\d.]+)")   # nur Ziffern und Punkt
    .astype(float)
    .fillna(0)                  # fehlende Werte als 0
)

# GeoDataFrame
gdf = gpd.GeoDataFrame(
    df,
    geometry=gpd.points_from_xy(df["Longitude"], df["Latitude"]),
    crs="EPSG:4326"
)

# Basiskarte
world = gpd.read_file(geodatasets.get_path("naturalearth.land"))


# Plot
fig, ax = plt.subplots(figsize=(10, 6))
world.plot(ax=ax, color="lightgray", edgecolor="black")

# Punkte nach Aschemächtigkeit einfärben (logarithmisch skaliert)
sc = ax.scatter(
    gdf["Longitude"], gdf["Latitude"],
    c=gdf["Thickness_cm_clean"],
    cmap="inferno",
    s=80, edgecolor="black", linewidth=0.5,
    norm=LogNorm(vmin=max(gdf["Thickness_cm_clean"].min(), 0.1),  # keine log(0)
                 vmax=gdf["Thickness_cm_clean"].max())
)


# Achsenbereich etwas erweitern
lon_min, lon_max = gdf["Longitude"].min(), gdf["Longitude"].max()
lat_min, lat_max = gdf["Latitude"].min(), gdf["Latitude"].max()
lon_pad = 0.9 * (lon_max - lon_min)
lat_pad = 0.9 * (lat_max - lat_min)
ax.set_xlim(lon_min - lon_pad, lon_max + lon_pad)
ax.set_ylim(lat_min - lat_pad, lat_max + lat_pad)

# Titel und Beschriftung
ax.set_title("Ash Fall Measurements (Tambora 1815)", fontsize=14)
ax.set_xlabel("Longitude")
ax.set_ylabel("Latitude")




# Punkte und Werte (nur >0 verwenden)
mask = gdf["Thickness_cm_clean"] > 0
x = gdf.loc[mask, "Longitude"].values
y = gdf.loc[mask, "Latitude"].values
z = gdf.loc[mask, "Thickness_cm_clean"].values

# Gitter für Karte
xi = np.linspace(lon_min - lon_pad, lon_max + lon_pad, 300)
yi = np.linspace(lat_min - lat_pad, lat_max + lat_pad, 300)
XI, YI = np.meshgrid(xi, yi)

rbf = sp.interpolate.Rbf(x, y, z, function="linear")

ZI = rbf(XI, YI)
# Problematische Werte abfangen
ZI = np.nan_to_num(ZI, nan=0.0, posinf=np.nanmax(z), neginf=0.0)
ZI = np.clip(ZI, 0, np.nanmax(z))


# Negative oder NaN-Werte abfangen
ZI = np.nan_to_num(ZI, nan=0.0)
ZI = np.clip(ZI, 0, None)

# Farbskala: grün → gelb → orange → rot 
base_colors = ["#00cc66", "#ffff66", "#ff9933", "#cc0000"]
base_cmap = LinearSegmentedColormap.from_list("ashfall_base", base_colors, N=256)

# Transparenz (Alpha) an kleine Werte koppeln 
N = 256
colors = base_cmap(np.linspace(0, 1, N))

# Farb-Alpha anpassen (kleine Werte kräftiger sichtbar)
alphas = np.linspace(0.4, 1.0, N)    # Start höher (0.4 statt 0.2)
cutoff = int(N * 0.5)                # nur untere Hälfte wird leicht transparenter
alphas[:cutoff] = np.linspace(0.4, 0.8, cutoff)
colors[:, -1] = alphas
cmap_transparent = ListedColormap(colors)

# Log-Norm so erweitern, dass 0.02 cm noch in Skala liegt
norm = LogNorm(vmin=0.02, vmax=max(gdf["Thickness_cm_clean"].max(), 100))




# Interpolationsplot 
im = ax.imshow(
    ZI,
    extent=(xi.min(), xi.max(), yi.min(), yi.max()),
    origin="lower",
    cmap=cmap_transparent,
    norm=norm,
    alpha=1.0,
    zorder=1
)

# Farbskala
cbar = plt.colorbar(im, ax=ax, shrink=0.85)
cbar.set_label("Ash thickness [cm] (log scale, < 0.1 cm transparent)")
cbar.ax.set_yticks([0.1, 0.3, 1, 3, 10, 30, 100])
cbar.ax.set_yticklabels(["0.1", "0.3", "1", "3", "10", "30", "100"])

plt.tight_layout()
plt.show()

