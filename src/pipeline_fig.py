import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

OUT = r"c:\NetworkScience"
stages = [
    ("1. Parse royal92 GEDCOM", "3,010 individuals, 1,422 families"),
    ("2. Harvest Wikidata", "descendant closures of 10 roots\n+ married-in spouses"),
    ("3. Record linkage", "name+year, exact-date rescue\n0 duplicates vs. original"),
    ("4. Merge & clean", "blood-only (drop adopted/foster),\nprune impossible dates"),
    ("5. Nobility & filters", "P97/P53 -> noble vs. commoner;\nfiltering ladder"),
    ("6. Analysis", "structure, centrality, communities,\npropagation, visualization"),
]
colors = ["#2b6cb0", "#2b8a6c", "#8a6d2b", "#8a2b52", "#5a2b8a", "#333a4d"]

fig, ax = plt.subplots(figsize=(4.2, 8.4))
n = len(stages)
h, gap = 1.0, 0.55
for i, ((title, sub), col) in enumerate(zip(stages, colors)):
    y = (n - 1 - i) * (h + gap)
    box = FancyBboxPatch((0, y), 4, h, boxstyle="round,pad=0.02,rounding_size=0.12",
                         linewidth=0, facecolor=col)
    ax.add_patch(box)
    ax.text(2, y + h * 0.63, title, ha="center", va="center", color="white",
            fontsize=11, fontweight="bold")
    ax.text(2, y + h * 0.26, sub, ha="center", va="center", color="#e8ebf2", fontsize=8)
    if i < n - 1:
        ax.add_patch(FancyArrowPatch((2, y), (2, y - gap),
                     arrowstyle="-|>", mutation_scale=16, color="#9aa0ad", linewidth=1.5))

ax.set_xlim(-0.2, 4.2)
ax.set_ylim(-0.2, n * (h + gap))
ax.axis("off")
fig.tight_layout()
fig.savefig(rf"{OUT}\fig_pipeline.png", dpi=170, bbox_inches="tight")
print("Wrote fig_pipeline.png")
