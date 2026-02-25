import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt

# ============================================================
# 1) Manual ash area input (km²)
# ============================================================

data = {
    "Threshold [cm]": [0, 0.1, 1, 10, 100],

    "Indonesia": [
        1.183283e+06,
        789120.150952,
        222589.747036,
        32716.948923,
        565.316881
    ],

    "Malaysia": [
        2.035683e+05,
        5974.337417,
        np.nan,
        np.nan,
        np.nan
    ],

    "Australia": [
        7.308464e+04,
        1480.268862,
        np.nan,
        np.nan,
        np.nan
    ],

    "Philippines": [
        2.146486e+04,
        np.nan,
        np.nan,
        np.nan,
        np.nan
    ],

    "East Timor": [
        1.471082e+04,
        14710.819729,
        31.257266,
        np.nan,
        np.nan
    ],

    "Brunei": [
        1.069880e+04,
        np.nan,
        np.nan,
        np.nan,
        np.nan
    ],
}

df = pd.DataFrame(data)

# ============================================================
# 2) Load country areas (Equal Area)
# ============================================================

path = r"C:\Users\jjona\Documents\Uni\Master\Klima\python_tambora\ne_110m_admin_0_countries.shp"
world = gpd.read_file(path)

world_eq = world.to_crs("EPSG:6933")
world_eq["area_km2"] = world_eq.area / 1e6
country_area = world_eq.set_index("ADMIN")["area_km2"]

# ============================================================
# 3) Convert km² → % of country
# ============================================================

for country in df.columns[1:]:
    total = country_area.get(country, np.nan)
    df[country] = df[country] / total * 100.0

# ============================================================
# 4) Plot
# ============================================================

plt.rcParams.update({
    "font.size": 10,
    "axes.titlesize": 11,
    "axes.labelsize": 10,
})

fig, ax = plt.subplots(figsize=(6.6, 4.2))

x = df["Threshold [cm]"].values

for country in df.columns[1:]:
    y = df[country].values

    ax.plot(
        x, y,
        marker="o",
        linewidth=2,
        label=country
    )

# Axes
ax.set_xscale("log")
ax.set_xlabel("Ash thickness threshold [cm]")
ax.set_ylabel("Affected share of country [%]")

ax.set_xticks([0.1, 1, 10, 100])
ax.get_xaxis().set_major_formatter(plt.ScalarFormatter())

ax.grid(True, linestyle=":", linewidth=0.7)

# Legend
ax.legend(title="Country", frameon=True)

plt.tight_layout()

# Export (paper)
plt.savefig("country_exposure_vs_threshold.pdf", bbox_inches="tight")
plt.savefig("country_exposure_vs_threshold.png", dpi=600, bbox_inches="tight")

plt.show()
