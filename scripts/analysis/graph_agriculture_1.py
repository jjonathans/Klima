import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


THRESHOLDS = np.array([0.1, 1, 10, 100])
AGRI_CODES = [21, 31, 35, 40]

CODE_NAMES = {
    21: "Other agriculture",
    31: "Aquaculture",
    35: "Oil palm",
    40: "Rice paddy",
}

OUT_DIR = "agri_analysis"
os.makedirs(OUT_DIR, exist_ok=True)

OUT_PNG = os.path.join(OUT_DIR, "agri_combined_absolute_with_percent_axis.png")


# Helper: Datei laden

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


# Daten sammeln + Total-Agriculture-Fläche rekonstruieren

rows = []
total_area_estimates = {c: [] for c in AGRI_CODES}

for thr in THRESHOLDS:
    df = read_stats(thr)
    agri = df[df["code"].isin(AGRI_CODES)].copy()

    area_by_code = {c: 0.0 for c in AGRI_CODES}
    shareclass_by_code = {c: 0.0 for c in AGRI_CODES}

    for _, r in agri.iterrows():
        c = int(r["code"])
        area_by_code[c] = float(r["area_km2"]) if pd.notna(r["area_km2"]) else 0.0
        shareclass_by_code[c] = float(r["Anteil Klasse belegt [%]"]) if pd.notna(r["Anteil Klasse belegt [%]"]) else 0.0

    # Total (betroffene Agriculture) bei diesem Threshold
    total = float(sum(area_by_code.values()))

    # Denominator-Schätzung pro Klasse: total_class = affected / (share_class/100)
    for c in AGRI_CODES:
        affected = area_by_code[c]
        share = shareclass_by_code[c]
        if affected > 0 and share > 0:
            total_area_estimates[c].append(affected / (share / 100.0))

    row = {"threshold": float(thr), "total_km2": total}
    for c in AGRI_CODES:
        row[f"area_{c}"] = area_by_code[c]
    rows.append(row)

out = pd.DataFrame(rows).sort_values("threshold")

# robust: median über alle Thresholds je Klasse
total_agri_km2 = 0.0
for c, vals in total_area_estimates.items():
    if len(vals) > 0:
        total_agri_km2 += float(np.median(vals))

if total_agri_km2 <= 0:
    raise RuntimeError(
        "Konnte die Gesamt-Agriculture-Fläche nicht rekonstruieren. "
        "Prüfe, ob in deinen Dateien die Spalten 'Anteil Klasse belegt [%]' und 'area_km2' korrekt sind."
    )

print(f"[DEBUG] Estimated TOTAL agriculture area (21+31+35+40): {total_agri_km2:.2f} km²")



COLORS = {
    21: "#ffefc3",
    31: "#091077",
    35: "#9065d0",
    40: "#c71585",
}

x = out["threshold"].values

fig, ax = plt.subplots(figsize=(10, 6))

# Stacked bars (absolute km²)
widths = x * 0.8  # optisch ~80% der Dekade
bottom = np.zeros_like(x)

for c in AGRI_CODES:
    y = out[f"area_{c}"].values
    ax.bar(
        x, y,
        bottom=bottom,
        width=widths,
        align="center",
        label=CODE_NAMES[c],
        color=COLORS[c],
        edgecolor="black",
        linewidth=0.6
    )
    bottom += y

# linke Achse
ax.set_xscale("log")
ax.set_xlabel("Ash thickness threshold [cm]")
ax.set_ylabel("Affected agriculture area [km²]")

ax.set_xticks([0.1, 1, 10, 100])
ax.get_xaxis().set_major_formatter(plt.ScalarFormatter())

# kein Grid
ax.grid(False)


# Rechte Achse: Prozent von gesamter Agriculture (nur Skala)

def km2_to_pct(km2):
    return (km2 / total_agri_km2) * 100.0

def pct_to_km2(pct):
    return (pct / 100.0) * total_agri_km2

ax_right = ax.secondary_yaxis("right", functions=(km2_to_pct, pct_to_km2))
ax_right.set_ylabel("Affected share of total agriculture [%]")

# Legende
ax.legend(
    loc="upper left",
    bbox_to_anchor=(0.7, 1),
    frameon=True
)

plt.tight_layout()
plt.savefig(OUT_PNG, dpi=250, bbox_inches="tight")
plt.show()

print(f"[DONE] Plot gespeichert: {OUT_PNG}")
