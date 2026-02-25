import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# ============================================================
# Settings
# ============================================================

THRESHOLDS = np.array([0.1, 1, 10, 100])
AGRI_CODES = [21, 31, 35, 40]

CODE_NAMES = {
    21: "Other agriculture",
    31: "Aquaculture",
    35: "Oil palm",
    40: "Rice paddy",
}

COLORS = {
    21: "#ffefc3",
    31: "#091077",
    35: "#9065d0",
    40: "#c71585",
}

OUT_DIR = "agri_analysis"
os.makedirs(OUT_DIR, exist_ok=True)

OUT_PNG = os.path.join(OUT_DIR, "agri_relative_exposure_area.png")


# Helper

def read_stats(thr):

    thr_str = str(int(thr)) if float(thr).is_integer() else str(thr)

    xlsx = f"lulc_ash_stats_threshold_{thr_str}cm.xlsx"
    csv  = f"lulc_ash_stats_threshold_{thr_str}cm.csv"

    if os.path.exists(xlsx):
        df = pd.read_excel(xlsx)
    else:
        df = pd.read_csv(csv, sep=";")

    df["code"] = df["Klasse"].astype(str).str.extract(r"^\s*(\d+)\s*:").astype(int)
    return df



# Daten sammeln

rows = []

for thr in THRESHOLDS:

    df = read_stats(thr)
    agri = df[df["code"].isin(AGRI_CODES)]

    share = {c: 0.0 for c in AGRI_CODES}

    for _, r in agri.iterrows():
        c = int(r["code"])
        share[c] = float(r["Anteil Klasse belegt [%]"])

    row = {"threshold": thr}
    for c in AGRI_CODES:
        row[f"share_{c}"] = share[c]

    rows.append(row)

out = pd.DataFrame(rows).sort_values("threshold")


# Plot

x = out["threshold"].values

fig, ax = plt.subplots(figsize=(9, 5.5))

for c in AGRI_CODES:
    y = out[f"share_{c}"].values

    ax.plot(
        x, y,
        linewidth=2.4,
        color=COLORS[c],
        label=CODE_NAMES[c],
        zorder=3
    )

    ax.fill_between(
        x, y,
        alpha=0.95 if c == 21 else 0.25,   # gelb weniger transparent
        color=COLORS[c],
        edgecolor=COLORS[c],               # Kontur in gleicher Farbe
        linewidth=1.2,
        zorder=2
    )

# Achsen
ax.set_xscale("log")
ax.set_xlabel("Ash thickness threshold [cm]")
ax.set_ylabel("Affected share of class [%]")

ax.set_xticks([0.1, 1, 10, 100])
ax.get_xaxis().set_major_formatter(plt.ScalarFormatter())

ax.set_ylim(0, None)

ax.grid(True, which="both", linestyle=":", linewidth=0.8)
ax.legend(loc="best", frameon=True)

plt.tight_layout()
plt.savefig(OUT_PNG, dpi=250)
plt.show()

print(f"[DONE] Plot gespeichert: {OUT_PNG}")
