import json
import re
import math
from collections import defaultdict
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib import cm

OUT = r"c:\NetworkScience"
m = json.load(open(rf"{OUT}\royal_updated.json", encoding="utf-8"))
indi, fam = m["individuals"], m["families"]


def clean(x):
    return indi[x]["name"].replace("/", " ").replace("_", " ").strip()


children = defaultdict(list)
for f in fam.values():
    h, w = f.get("husb"), f.get("wife")
    for c in f.get("chil", []):
        if h:
            children[h].append(c)
        if w:
            children[w].append(c)

import networkx as nx
DG = nx.DiGraph()
for p, cs in children.items():
    for c in cs:
        DG.add_edge(p, c)
cands = ["Edward_I", "William_I the", "Cerdic", "Hugh   Capet", "Egbert",
         "Alfred the", "John of Brandenburg", "Christian_IX", "Victoria  Hanover"]
best, best_n = None, -1
for q in cands:
    hit = next((x for x in indi if q.lower().replace("_", " ") in clean(x).lower()), None)
    if hit and hit in DG:
        d = len(nx.descendants(DG, hit))
        if d > best_n:
            best, best_n = hit, d
root = best
print(f"root: {clean(root)} with {best_n} descendants")


pos = {}
leaf_counter = [0]
max_depth = [0]


def layout(x, depth, seen):
    seen.add(x)
    max_depth[0] = max(max_depth[0], depth)
    kids = [c for c in children.get(x, []) if c in indi and c not in seen]
    if not kids:
        a = leaf_counter[0]
        leaf_counter[0] += 1
        pos[x] = [a, depth]
        return a
    angs = [layout(c, depth + 1, seen) for c in kids]
    a = sum(angs) / len(angs)
    pos[x] = [a, depth]
    return a


layout(root, 0, set())
n_leaves = leaf_counter[0]

gap = 0.06
for x, (a, depth) in pos.items():
    theta = (a / max(n_leaves - 1, 1)) * (2 * math.pi * (1 - gap)) + math.pi / 2
    r = depth
    pos[x] = (theta, r)


fig, ax = plt.subplots(figsize=(11, 11), subplot_kw={"projection": "polar"})
fig.patch.set_facecolor("#0d0b14")
ax.set_facecolor("#0d0b14")

segs, cols = [], []
cmap = plt.get_cmap("twilight_shifted")
seen = set()


def edges(x):
    seen.add(x)
    th, r = pos[x]
    kids = [c for c in children.get(x, []) if c in indi and c not in seen]
    for c in kids:
        cth, cr = pos[c]

        arc = np.linspace(th, cth, 12)
        segs.append(np.column_stack([arc, np.full_like(arc, r)]))
        cols.append(cmap(r / max(max_depth[0], 1)))
        segs.append(np.array([[cth, r], [cth, cr]]))
        cols.append(cmap(cr / max(max_depth[0], 1)))
        edges(c)


edges(root)
lc = LineCollection(segs, colors=cols, linewidths=0.35, alpha=0.75)
ax.add_collection(lc)


leaves = [(th, r) for x, (th, r) in pos.items()
          if not [c for c in children.get(x, []) if c in indi]]
lt = [p[0] for p in leaves]
lr = [p[1] for p in leaves]
ax.scatter(lt, lr, s=1.1, c=[cmap(r / max(max_depth[0], 1)) for r in lr],
           alpha=0.9, linewidths=0)

ax.scatter([pos[root][0]], [0], s=60, c="#ffe9a8", zorder=5, edgecolors="#0d0b14")

ax.set_rmax(max_depth[0] + 0.5)
ax.axis("off")
ax.set_title(f"The Royal Descent Tree — {best_n + 1:,} blood descendants of "
             f"{clean(root)}", color="#e8e2f0", fontsize=13, pad=18)
fig.tight_layout()
fig.savefig(rf"{OUT}\fig_family_tree.png", dpi=200, bbox_inches="tight",
            facecolor=fig.get_facecolor())
print(f"Wrote fig_family_tree.png  ({best_n + 1} nodes, {max_depth[0]} generations)")
