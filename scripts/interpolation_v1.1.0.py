import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import geodatasets
from matplotlib.colors import LogNorm, LinearSegmentedColormap,ListedColormap, to_rgba
import scipy as sp
import numpy as np
from scipy.interpolate import Rbf, griddata

# ANSI colourcodes for console ouput
ANSI_BLACK = "\033[1;30m"
ANSI_RED = "\033[1;31m"
ANSI_GREEN = "\033[1;32m"
ANSI_YELLOW = "\033[1;33m"
ANSI_BLUE = "\033[1;34m"
ANSI_MAGENTA = "\033[1;35m"
ANSI_CYAN = "\033[1;36m"
ANSI_WHITE = "\033[1;37m"
ANSI_RESET = "\033[0m"

# mark start of interpreting python code
print(ANSI_MAGENTA + "Interpretation of interpolation_v2.py started." + ANSI_RESET)

# loading in cleaned .csv data file
df = pd.read_csv("data/tambora_ashfall01.csv")

# extracting ashfall thickness data
df["Thickness_cm"] = (
    df["Thickness_cm"]
    .astype(float)
)

# definition of our GeoDataFrame
gdf = gpd.GeoDataFrame(
    df,
    geometry=gpd.points_from_xy(df["Longitude"], df["Latitude"]),
    crs="EPSG:4326"
)

# reading in a world map
world = gpd.read_file(geodatasets.get_path("naturalearth.land"))

# plotting part of the world map
fig, ax = plt.subplots(figsize=(10, 6))
world.plot(ax=ax, color="lightgray", edgecolor="black")

# colour points considering ash thickness on a log scale
sc = ax.scatter(
    gdf["Longitude"], gdf["Latitude"],
    c=gdf["Thickness_cm"],
    cmap="inferno",
    s=80, edgecolor="black", linewidth=0.5,
    norm=LogNorm(vmin=max(gdf["Thickness_cm"].min(), 0.1),  # keine log(0)
                 vmax=gdf["Thickness_cm"].max())
)

# adjust axes of world map to center relevant part with reasonable zoom
lon_min, lon_max = gdf["Longitude"].min(), gdf["Longitude"].max()
lat_min, lat_max = gdf["Latitude"].min(), gdf["Latitude"].max()
lon_pad = 0.9 * (lon_max - lon_min)
lat_pad = 0.9 * (lat_max - lat_min)
ax.set_xlim(lon_min - lon_pad, lon_max + lon_pad)
ax.set_ylim(lat_min - lat_pad, lat_max + lat_pad)

# title and axis descriptions
ax.set_title("Ash Fall Measurements (Tambora 1815)", fontsize=14)
ax.set_xlabel("Longitude")
ax.set_ylabel("Latitude")

# match points and values
mask = gdf["Thickness_cm"] > 0
x = gdf.loc[mask, "Longitude"].values
y = gdf.loc[mask, "Latitude"].values
z = gdf.loc[mask, "Thickness_cm"].values

# introduce lattice for map
xi = np.linspace(lon_min - lon_pad, lon_max + lon_pad, 300)
yi = np.linspace(lat_min - lat_pad, lat_max + lat_pad, 300)
rbf = sp.interpolate.Rbf(x, y, z, function="linear")
XI, YI = np.meshgrid(xi, yi)
ZI = rbf(XI, YI)

# catch problematic values
ZI = np.nan_to_num(ZI, nan=0.0, posinf=np.nanmax(z), neginf=0.0)
ZI = np.clip(ZI, 0, np.nanmax(z))
# catch especially negative or nan values
ZI = np.nan_to_num(ZI, nan=0.0)
ZI = np.clip(ZI, 0, None)

# colourscheme for ashfall interpolation: green → yellow → orange → red
base_colors = ["#00cc66", "#ffff66", "#ff9933", "#cc0000"]
base_cmap = LinearSegmentedColormap.from_list("ashfall_base", base_colors, N=256)

# couple transparency alpha with small values
N = 256
colors = base_cmap(np.linspace(0, 1, N))

# adjust colour alpha to give small values increased visibilty
alphas = np.linspace(0.4, 1.0, N)    # increasing starting value (0.4 instead of 0.2)
cutoff = int(N * 0.5)                # limit increased transparency onto lower half
alphas[:cutoff] = np.linspace(0.4, 0.8, cutoff)
colors[:, -1] = alphas
cmap_transparent = ListedColormap(colors)

# enlarging norm lof log so that 0.02 is visible on the scale
norm = LogNorm(vmin=0.02, vmax=max(gdf["Thickness_cm"].max(), 100))

# plot of the interpolation of ashfall thickness data 
im = ax.imshow(
    ZI,
    extent=(xi.min(), xi.max(), yi.min(), yi.max()),
    origin="lower",
    cmap=cmap_transparent,
    norm=norm,
    alpha=1.0,
    zorder=1
)

# apply colour scheme to interpolated data
cbar = plt.colorbar(im, ax=ax, shrink=0.85)
cbar.set_label("Ash thickness [cm] (log scale, < 0.1 cm transparent)")
cbar.ax.set_yticks([0.1, 0.3, 1, 3, 10, 30, 100])
cbar.ax.set_yticklabels(["0.1", "0.3", "1", "3", "10", "30", "100"])
plt.tight_layout()
plt.show()

# mark end of interpreting python code --- shows only up after closing canvas
print(ANSI_MAGENTA + "Interpretation of interpolation_v2.py finished (successfully)." + ANSI_RESET)
