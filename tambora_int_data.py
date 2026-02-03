import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import geodatasets

import numpy as np

from scipy.interpolate import Rbf
from scipy.spatial import cKDTree
from scipy.ndimage import binary_fill_holes, binary_closing, binary_opening

import rasterio
from rasterio.enums import Resampling
from rasterio.vrt import WarpedVRT
from rasterio.transform import from_bounds
from rasterio.features import shapes, geometry_mask
from rasterio.features import sieve

from shapely.geometry import shape
from matplotlib.colors import LogNorm, ListedColormap, to_rgba

import matplotlib.patches as mpatches




# Länder-Shapefile laden (brauche ich später, um betroffene Länder zu finden)
path = r"C:\Users\jjona\Documents\Uni\Master\Klima\python_tambora\ne_110m_admin_0_countries.shp"
world_countries = gpd.read_file(path)
world_countries = world_countries.to_crs("EPSG:4326")  # alles in lon/lat
print(world_countries.columns)


# Tambora Messdaten laden
df = pd.read_csv("tambora_ashfall.csv")

# Thickness-Spalte ist nicht sauber numerisch -> ich extrahiere nur die Zahl
# z.B. "12 cm" -> 12
df["Thickness_cm_clean"] = (
    df["Thickness_cm"]
    .astype(str)
    .str.extract(r"([\d.]+)")
    .astype(float)
    .fillna(0)
)

# aus Lon/Lat richtige Geometrie bauen
gdf = gpd.GeoDataFrame(
    df,
    geometry=gpd.points_from_xy(df["Longitude"], df["Latitude"]),
    crs="EPSG:4326"
)


# Weltkarte als Hintergrund (nur Landflächen)
world = gpd.read_file(geodatasets.get_path("naturalearth.land"))

fig, ax = plt.subplots(figsize=(12, 6))
world.plot(ax=ax, color="#dddddd", edgecolor="#555555", linewidth=0.5)


# Jetzt das Landuse Raster laden (indo_agri_map.tif)
# Ziel: als Raster overlay plotten, aber nicht mit voller Auflösung -> sonst zu groß/langsam
with rasterio.open("indo_agri_map.tif") as src:
    if src.crs is None:
        raise RuntimeError("indo_agri_map.tif hat kein CRS – bitte prüfen.")

    # ich will am Ende immer EPSG:4326
    if src.crs.to_string() != "EPSG:4326":
        # falls CRS anders ist, warp (Reprojektion) on the fly
        with WarpedVRT(src, crs="EPSG:4326") as vrt:
            width, height = vrt.width, vrt.height

            # Downsampling: max ca. 2000 px pro Richtung, sonst wird plotting extrem langsam
            max_size = 2000
            scale = max(width / max_size, height / max_size, 1)
            out_w = int(width / scale)
            out_h = int(height / scale)

            lulc = vrt.read(
                1,
                out_shape=(out_h, out_w),
                resampling=Resampling.nearest,  # Klassen -> nearest ist richtig
                out_dtype="uint8",
            )
            bounds = vrt.bounds
    else:
        # wenn es eh schon EPSG:4326 ist: einfach nur resamplen
        width, height = src.width, src.height
        max_size = 2000
        scale = max(width / max_size, height / max_size, 1)
        out_w = int(width / scale)

        # das out_h war bei dir etwas "speziell" formuliert -> lasse ich exakt so
        out_h = int(height / max_size) if height / max_size > width / max_size else int(height / scale)

        lulc = src.read(
            1,
            out_shape=(out_h, out_w),
            resampling=Resampling.nearest,
            out_dtype="uint8",
        )
        bounds = src.bounds

# Extent ist wichtig fürs Plotting (imshow braucht das)
extent = (bounds.left, bounds.right, bounds.bottom, bounds.top)


# hier definierst du die Klassenfarben (MapBiomas)
# 0 ist Hintergrund / NoData -> transparent
class_info = {
    0:  {"name": "NoData / background",          "color": (0, 0, 0, 0)},
    3:  {"name": "Forest formation",             "color": "#1f8d49"},
    5:  {"name": "Mangrove",                     "color": "#04381d"},
    9:  {"name": "Planted forest",               "color": "#7a5900"},
    13: {"name": "Other natural vegetation",     "color": "#d89f5c"},
    21: {"name": "Other agriculture",            "color": "#ffefc3"},
    24: {"name": "Urban area",                   "color": "#d4271e"},
    25: {"name": "Other non-vegetation",         "color": "#db4d4f"},
    30: {"name": "Mining pit",                   "color": "#9c0027"},
    31: {"name": "Aquaculture",                  "color": "#091077"},
    33: {"name": "River / Lake / Ocean",         "color": "#2532e4"},
    35: {"name": "Oil palm",                     "color": "#9065d0"},
    40: {"name": "Rice paddy",                   "color": "#c71585"},
    76: {"name": "Peat swamp forest",            "color": "#2f7360"},
}

# colormap als Array: Index ist direkt der LULC-Code im Raster
max_code = int(np.max(lulc))
cmap_arr = np.zeros((max_code + 1, 4))
for code, info in class_info.items():
    cmap_arr[code] = to_rgba(info["color"])
lulc_cmap = ListedColormap(cmap_arr)


# LULC Raster plotten
# zorder=1 heißt: kommt vor Weltkarte, aber unter Ash overlay
ax.imshow(
    lulc,
    cmap=lulc_cmap,
    extent=extent,
    origin="upper",
    zorder=1
)

# damit die Karte nicht irgendwo "reinzoomt": Grenzen der ganzen Welt setzen
minx, miny, maxx, maxy = world.total_bounds
ax.set_xlim(minx, maxx)
ax.set_ylim(miny, maxy)


# jetzt kommt der Interpolationsteil für Asche
# ich nehme nur die Messpunkte mit thickness > 0, weil sonst log nicht geht
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

# Schutz, damit RBF nicht komplett Müll macht
if len(z) < 5:
    raise RuntimeError("Zu wenige valide Messpunkte für eine sinnvolle Interpolation.")

# Grid definieren (hier 600x600)
nx, ny = 600, 600
xi = np.linspace(xmin, xmax, nx)
yi = np.linspace(ymin, ymax, ny)
XI, YI = np.meshgrid(xi, yi)

# Interpolation in log10 ist stabiler, weil thickness extrem stark variiert
eps = 1e-3
z_log = np.log10(z + eps)

rbf = Rbf(x, y, z_log, function="linear", smooth=.005)
ZI_log = rbf(XI, YI)

# zurücktransformieren
ZI = (10**ZI_log) - eps

# negative/kleine Artefakte rauswerfen
ZI[ZI <= 0] = np.nan

# Clipping gegen Ausreißer (damit farbscale nicht kaputt ist)
ZI = np.clip(ZI, 0, 1.2*np.nanmax(z))


# hier baust du das "physikalische" Ausklingen rein:
# Zentrum = Tambora, außen abfallend, Süden stärker
lon0, lat0 = 118.0, -8.25

dx = (XI - lon0) * np.cos(np.deg2rad(lat0))  # lon auf Breitenkreis skalieren
dy = (YI - lat0)

south_boost = 2
dy_eff = np.where(dy < 0, dy * south_boost, dy)

# effektive Distanz in Grad
r = np.sqrt(dx*dx + dy_eff*dy_eff)

# Taper: bis r0 voll, dann linear bis r1 -> 0
r0 = 3.5
r1 = 20.0

w = np.ones_like(r, dtype=float)
mid = (r > r0) & (r < r1)
w[mid] = 1.0 - (r[mid] - r0) / (r1 - r0)
w[r >= r1] = 0.0

ZI = ZI * w

# falls wirklich harte 0 gewollt ist
ZI[w == 0.0] = 0.0


# nächster Punkt: dist zur nächsten Messung (gerade ungenutzt)
# wurde als cutoff genutzt, sorgt für unsauberes bild
tree = cKDTree(np.column_stack([x, y]))
dist, _ = tree.query(np.column_stack([XI.ravel(), YI.ravel()]), k=1)
dist = dist.reshape(XI.shape)

# Beispiel: harter cutoff (bei dir auskommentiert)
# dmax = 12.0
# ZI[dist > dmax] = np.nan


# Plot: colormap log-skaliert, damit man alles sieht
vmin = max(np.nanmin(ZI[ZI > 0]), 0.05)
vmax = np.nanmax(ZI)
norm = LogNorm(vmin=vmin, vmax=vmax)

from scipy.ndimage import binary_fill_holes, binary_closing, binary_opening
from rasterio.features import sieve

threshold_plot = 100  #Plot-Threshold in cm

M = (ZI >= threshold_plot) & np.isfinite(ZI)

M = binary_fill_holes(M)
M = binary_closing(M, iterations=2)
M = binary_fill_holes(M)

# 6) Jetzt plotten: außerhalb Maske unsichtbar
ZI_masked = np.where(M, ZI, np.nan)

im = ax.pcolormesh(
    XI, YI, ZI_masked,
    shading="auto",
    cmap="inferno",
    norm=norm,
    alpha=0.55,
    zorder=2.0
)

# Messpunkte > 0 als Scatter
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

# Messpunkte = 0 separat (sonst gehen die in der log cmap unter)
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

# Achsen nochmal wirklich auf Welt setzen 
minx, miny, maxx, maxy = world.total_bounds
ax.set_xlim(minx, maxx)
ax.set_ylim(miny, maxy)

# Colorbar + sinnvolle log ticks
cbar = plt.colorbar(im, ax=ax, shrink=0.85)
cbar.set_label("Ash thickness [cm] (log scale)")
ticks = np.array([0.1, 0.3, 1, 3, 10, 30, 100])
ticks = ticks[(ticks >= vmin) & (ticks <= vmax)]
cbar.set_ticks(ticks)
cbar.set_ticklabels([str(t) for t in ticks])

ax.set_xlabel("Longitude")
ax.set_ylabel("Latitude")
ax.legend(loc="upper right")


threshold_calc = 0.1  # <- dein Rechen-Threshold

# 1) Binärmaske für Polygonisierung
mask = (ZI > threshold_calc) & np.isfinite(ZI)

# 2) Löcher füllen (wichtig!)
mask = binary_fill_holes(mask)

# 3) Glätten: Closing verbindet, Opening entfernt dünne Ausläufer
mask = binary_closing(mask, iterations=2)
mask = binary_opening(mask, iterations=1)

mask_uint8 = mask.astype("uint8")

# 4) Kleine Inseln entfernen (Pixelanzahl; musst du einstellen)
MIN_PIXELS = 500   # Startwert: 200..1000 (bei 600x600)
mask_uint8 = sieve(mask_uint8, size=MIN_PIXELS)

# optional nochmal Löcher füllen (falls sieve neue Löcher erzeugt)
mask_uint8 = binary_fill_holes(mask_uint8.astype(bool)).astype("uint8")


transform = from_bounds(xmin, ymin, xmax, ymax, nx, ny)

geoms = []
for geom, val in shapes(mask_uint8, mask=mask_uint8, transform=transform):
    if val == 1:
        geoms.append(shape(geom))

ash_gdf = gpd.GeoDataFrame(geometry=geoms, crs="EPSG:4326")

# dissolve -> ein großes MultiPolygon statt tausend Einzelteile
ash_union = ash_gdf.dissolve()


# als nächstes: Aschepolygon auf das LULC Raster "rasterisieren"
# dadruch pixel zählen
left, right, bottom, top = extent
height, width = lulc.shape

lulc_transform = from_bounds(left, bottom, right, top, width, height)

ash_mask = geometry_mask(
    ash_union.geometry,
    transform=lulc_transform,
    invert=True,
    out_shape=(height, width)
)

# LULC in ash: außerhalb -> 0
lulc_in_ash = lulc.copy()
lulc_in_ash[~ash_mask] = 0

# Pixel count pro Klasse (innerhalb Aschegebiet)
vals_ash, counts_ash = np.unique(lulc_in_ash[lulc_in_ash != 0], return_counts=True)

# Pixel count pro Klasse in gesamtem Raster (für "wie viel % der Klasse betroffen")
vals_full, counts_full = np.unique(lulc[lulc != 0], return_counts=True)
total_full = dict(zip(vals_full.astype(int), counts_full))

total_pixels_ash = counts_ash.sum()

print(f"\n=== LULC-Klassen mit Asche > {threshold_calc} cm (auf resampeltem Grid) ===\n")
print("Code | Klasse                      | Pixels (Ash) | Anteil an Ash | Anteil Klasse belegt")
print("-"*90)

for code, cnt in zip(vals_ash.astype(int), counts_ash):
    info = class_info.get(code, {"name": "Unknown", "color": "#000000"})
    name = info["name"]

    share_ash = cnt / total_pixels_ash * 100 if total_pixels_ash > 0 else 0.0

    total_class = total_full.get(code, 0)
    share_class = cnt / total_class * 100 if total_class > 0 else 0.0

    print(f"{code:4d} | {name:27s} | {cnt:11d} | {share_ash:11.2f}% | {share_class:18.2f}%")


# Länder schneiden: intersection (Länderpolygon ∩ Aschepolygon)
affected = gpd.overlay(world_countries, ash_union, how="intersection")

countries = sorted(affected["ADMIN"].unique())
print("Betroffene Länder:")
for c in countries:
    print(" -", c)

# Flächen korrekt nur in Equal Area bestimmen (EPSG:6933)
affected_eq = affected.to_crs("EPSG:6933")
affected_eq["area_km2"] = affected_eq.area / 1e6

land_area = affected_eq.groupby("ADMIN")["area_km2"].sum().sort_values(ascending=False)
print(land_area)


# für Indonesien noch die grobe Aufteilung nach LULC-Klasse
lulc_stats = {}

for code, cnt in zip(vals_ash.astype(int), counts_ash):
    info = class_info.get(code, {"name": "Unknown", "color": "#000000"})
    name = info["name"]

    share_ash = cnt / total_pixels_ash * 100
    total_class = total_full.get(code, 0)
    share_class = cnt / total_class * 100 if total_class > 0 else 0.0

    lulc_stats[code] = {
        "name": name,
        "pixels_ash": cnt,
        "share_ash": share_ash,
        "share_class": share_class,
    }

area_ash_idn = land_area["Indonesia"]  # km² Aschefläche in Indonesien

for code, s in lulc_stats.items():
    frac = s["share_ash"] / 100.0
    area_class_km2 = area_ash_idn * frac
    print(f"{code:3d}  {s['name']:27s}  ~ {area_class_km2:10.1f} km² unter Asche > {threshold_calc} cm in Indonesien")


# Legende für die LULC Klassen 
legend_patches = []
for code, info in class_info.items():
    if code == 0:
        continue
    legend_patches.append(
        mpatches.Patch(
            color=info["color"],
            label=f"{code}: {info['name']}"
        )
    )

ax.legend(
    handles=legend_patches,
    title="MapBiomas Classes",
    loc="lower left",
    fontsize=7
)

plt.tight_layout()
plt.show()
