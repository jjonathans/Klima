import numpy as np
import matplotlib.pyplot as plt

# ------------------------------------------------------------
# Parameters (same as interpolation code)
# ------------------------------------------------------------
r0 = 2.0
r1 = 16.5
south_boost = 2.0

# Grid for schematic
x = np.linspace(-20, 20, 400)
y = np.linspace(-20, 20, 400)
X, Y = np.meshgrid(x, y)

# Tambora center at (0,0)
dx = X
dy = Y

# South boost
dy_eff = np.where(dy < 0, dy * south_boost, dy)

# Effective distance
R = np.sqrt(dx**2 + dy_eff**2)

# Taper function
W = np.ones_like(R)

mid = (R > r0) & (R < r1)
W[mid] = 1 - (R[mid] - r0) / (r1 - r0)
W[R >= r1] = 0

# ------------------------------------------------------------
# Plot schematic
# ------------------------------------------------------------
fig, ax = plt.subplots(figsize=(7, 6))

im = ax.contourf(
    X, Y, W,
    levels=20,
    cmap="viridis"
)

# Radii circles (north symmetric reference)
circle_r0 = plt.Circle((0, 0), r0, color="white", fill=False, linewidth=2)
circle_r1 = plt.Circle((0, 0), r1, color="white", fill=False, linewidth=2, linestyle="--")

ax.add_patch(circle_r0)
ax.add_patch(circle_r1)

# Volcano center
ax.scatter(0, 0, color="red", s=80, zorder=5)
ax.text(0, 0.8, "Tambora", ha="center", color="red")

# Direction labels
ax.text(0, 18, "North", ha="center")
ax.text(0, -19, "South (boosted decay)", ha="center")

# Radius labels
ax.text(r0 + 0.5, 0, "r₀ = 2°", color="white")
ax.text(r1 - 2.5 , -9.5, "r₁ = 16.5°", color="white")

# Layout
ax.set_aspect("equal")
ax.set_xlabel("Longitude distance (scaled)")
ax.set_ylabel("Latitude distance")
ax.set_title("Directional taper function for ash interpolation")

cbar = plt.colorbar(im, ax=ax)
cbar.set_label("Weight w(r)")

plt.tight_layout()
plt.show()
