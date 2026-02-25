import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt

# ============================================================
# Paper-quality dual-metric chart:
#   bars  = affected land area [km²]
#   dots  = affected share of country [%] (top x-axis)
#   clean layout, consistent typography, export as PDF/PNG
# ============================================================

# --- manual input (km²) ---
'''
ash_area_km2 = {
    "Indonesia":   789120.150952,
    "East Timor":   14710.819729,
    "Malaysia":      5974.337417,
    "Australia":     1480.268862,
}
'''
ash_area_km2 = {
    "Indonesia":      1.183283e+06,
    "Malaysia":       2.035683e+05,
    "Australia":      7.308464e+04,
    "Philippines":    2.146486e+04,
    "East Timor":     1.471082e+04,
    "Brunei":         1.069880e+04,
}
# Optional: only if your shapefile uses different naming
name_alias = {
    # "East Timor": "Timor-Leste",
}

# --- load countries + compute total country areas (Equal Area) ---
path = r"C:\Users\jjona\Documents\Uni\Master\Klima\python_tambora\ne_110m_admin_0_countries.shp"
world_countries = gpd.read_file(path)

world_eq = world_countries.to_crs("EPSG:6933")
world_eq["total_km2"] = world_eq.area / 1e6
total_area = world_eq.set_index("ADMIN")["total_km2"]

# --- build table ---
rows = []
for k, v in ash_area_km2.items():
    admin = name_alias.get(k, k)
    total = float(total_area.get(admin, np.nan))
    pct = (float(v) / total * 100.0) if (np.isfinite(total) and total > 0) else np.nan
    rows.append({
        "Country": k,
        "ADMIN": admin,
        "Ash area [km²]": float(v),
        "Total area [km²]": total,
        "Affected [%]": pct
    })

df = pd.DataFrame(rows)

# Sort (choose one):
# df = df.sort_values("Ash area [km²]", ascending=True).reset_index(drop=True)
df = df.sort_values("Affected [%]", ascending=True).reset_index(drop=True)  # paper-friendly: highlights relative impact

# ============================================================
# Plot styling (paper-like)
# ============================================================

plt.rcParams.update({
    "font.size": 10,
    "axes.titlesize": 11,
    "axes.labelsize": 10,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "legend.fontsize": 9,
    "axes.linewidth": 0.8,
})

fig, ax = plt.subplots(figsize=(6.6, 3.9))  # fits ~single-column width depending on journal

ypos = np.arange(len(df))

# Bars: affected area
ax.barh(
    ypos,
    df["Ash area [km²]"].values,
    height=0.70,
    color="#0b3c8c",        # dunkelblau
    edgecolor="black",
    linewidth=0.6,
)

ax.set_yticks(ypos)
ax.set_yticklabels(df["Country"].values)
ax.set_xlabel("Affected land area [km²]")

# Use scientific-ish x formatting (no commas in many journals)
ax.ticklabel_format(axis="x", style="sci", scilimits=(0, 0))
ax.xaxis.get_offset_text().set_size(9)

# Thin, unobtrusive grid only on x (helps reading)
ax.grid(True, axis="x", linestyle=":", linewidth=0.6, alpha=0.8)
ax.grid(False, axis="y")

# Secondary top axis: percent of country
ax2 = ax.twiny()
pmax = float(np.nanmax(df["Affected [%]"].values))
ax2.set_xlim(0, pmax * 1.10 if np.isfinite(pmax) and pmax > 0 else 1.0)

# Points (percent)
ax2.plot(
    df["Affected [%]"].values,
    ypos,
    marker="o",
    linestyle="None",
    markersize=5,
    markeredgewidth=0.8,
    markeredgecolor="black",
)

# Annotations (minimal, paper-friendly)
# - annotate % values right of markers
for i, p in enumerate(df["Affected [%]"].values):
    if np.isfinite(p):
        ax2.text(p + 0.02 * pmax, i, f"{p:.2f}", va="center", ha="left", fontsize=9)

# - annotate km² only for the largest bar (optional, reduces clutter)
# Uncomment if you want all bars labeled:
# xmax = float(df["Ash area [km²]"].max())
# for i, v in enumerate(df["Ash area [km²]"].values):
#     ax.text(v + 0.01 * xmax, i, f"{v:.0f}", va="center", fontsize=9)


# Clean spines (keep left/bottom/top neat)
ax.spines["right"].set_visible(False)
ax2.spines["right"].set_visible(False)

plt.tight_layout()

# ============================================================
# Export (recommended for paper)
# ============================================================
out_pdf = "fig_country_impact_dualmetric.pdf"
out_png = "fig_country_impact_dualmetric.png"
plt.savefig(out_pdf, bbox_inches="tight")
plt.savefig(out_png, dpi=600, bbox_inches="tight")

plt.show()

print(df[["Country", "Ash area [km²]", "Affected [%]"]].sort_values("Affected [%]", ascending=False))




