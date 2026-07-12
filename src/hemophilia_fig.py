import json
import re
import sys
import math
from collections import defaultdict
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
OUT = r"c:\NetworkScience"
model = json.load(open(rf"{OUT}\royal_updated.json", encoding="utf-8"))
indi, fam = model["individuals"], model["families"]


def yr(s):
    m = re.search(r"(\d{4})", s or "")
    return int(m.group(1)) if m else 3000


def clean(x):
    return indi[x]["name"].replace("/", " ").replace("_", " ").strip()


father, mother, children = {}, {}, defaultdict(list)
for f in fam.values():
    h, w = f.get("husb"), f.get("wife")
    for c in f.get("chil", []):
        if h:
            father[c] = h; children[h].append(c)
        if w:
            mother[c] = w; children[w].append(c)

VICTORIA = "@I1@"
desc, stack = set(), [VICTORIA]
while stack:
    v = stack.pop()
    for c in children.get(v, []):
        if c not in desc:
            desc.add(c); stack.append(c)

order = [VICTORIA] + sorted(desc, key=lambda x: yr(indi[x].get("birth_date", "")))
e = {VICTORIA: 1.0}
for v in order:
    if v == VICTORIA:
        continue
    sex = indi[v].get("sex", "")
    em = e.get(mother.get(v), 0.0) / 2.0
    ef = e.get(father.get(v), 0.0) if sex == "F" else 0.0
    e[v] = em + ef


placed = set()
kids = defaultdict(list)


def build(x):
    placed.add(x)
    for c in children.get(x, []):
        if c in desc and c not in placed:
            kids[x].append(c)
            build(c)


build(VICTORIA)
pos = {}
leaf = [0]
maxd = [0]


def layout(x, depth):
    maxd[0] = max(maxd[0], depth)
    ks = kids.get(x, [])
    if not ks:
        a = leaf[0]; leaf[0] += 1; pos[x] = [a, depth]; return a
    angs = [layout(c, depth + 1) for c in ks]
    a = sum(angs) / len(angs); pos[x] = [a, depth]; return a


layout(VICTORIA, 0)
nL = leaf[0]
for x, (a, d) in pos.items():
    pos[x] = ((a / max(nL - 1, 1)) * 2 * math.pi, d)

fig, ax = plt.subplots(figsize=(11, 11), subplot_kw={"projection": "polar"})
fig.patch.set_facecolor("#0a0a0f")
ax.set_facecolor("#0a0a0f")


segs = []
for p, ks in kids.items():
    pth, pr = pos[p]
    for c in ks:
        cth, cr = pos[c]
        arc = np.linspace(pth, cth, 8)
        segs.append(np.column_stack([arc, np.full_like(arc, pr)]))
        segs.append(np.array([[cth, pr], [cth, cr]]))
ax.add_collection(LineCollection(segs, colors="#2a2540", linewidths=0.3, alpha=0.6))


th = np.array([pos[x][0] for x in pos])
r = np.array([pos[x][1] for x in pos])
ev = np.array([e.get(x, 0.0) for x in pos])
order_idx = np.argsort(ev)
sizes = 3 + 90 * ev
cmap = plt.get_cmap("inferno")
sc = ax.scatter(th[order_idx], r[order_idx], s=sizes[order_idx],
                c=ev[order_idx], cmap=cmap, vmin=0, vmax=0.5,
                linewidths=0, alpha=0.95)
ax.scatter([pos[VICTORIA][0]], [0], s=160, marker="*", c="#fff2b0",
           zorder=6, edgecolors="#0a0a0f", linewidths=0.6)


cand = [(p, v) for v, p in e.items()
        if v != VICTORIA and pos.get(v) and pos[v][1] >= 3 and p >= 0.2]
cand.sort(reverse=True)
seen_lab, picked = set(), []
for p, v in cand:
    key = round(pos[v][0], 1)
    if key in seen_lab:
        continue
    seen_lab.add(key); picked.append((p, v))
    if len(picked) >= 7:
        break
for p, v in picked:
    t, rr = pos[v]
    nm = clean(v).split("  ")[0].split(" of ")[0]
    ax.annotate(f"{nm} ({p:.2f})", (t, rr),
                textcoords="offset points", xytext=(4, 4),
                fontsize=7.5, color="#f0d890", alpha=0.95)

cbar = fig.colorbar(sc, ax=ax, shrink=0.5, pad=0.08)
cbar.set_label("expected allele dosage  (P affected / carrier)",
               color="#d8d4e0", fontsize=9)
cbar.ax.yaxis.set_tick_params(color="#d8d4e0")
plt.setp(plt.getp(cbar.ax.axes, "yticklabels"), color="#d8d4e0")

ax.set_rmax(maxd[0] + 0.5)
ax.axis("off")
ax.set_title("Propagation of the haemophilia allele through Queen Victoria's "
             "descendants", color="#ece8f2", fontsize=13, pad=18)
fig.savefig(rf"{OUT}\fig_hemophilia.png", dpi=200, bbox_inches="tight",
            facecolor=fig.get_facecolor())
aff = sum(p for v, p in e.items() if v != VICTORIA and indi[v]["sex"] == "M")
car = sum(p for v, p in e.items() if v != VICTORIA and indi[v]["sex"] == "F")
print(f"Wrote fig_hemophilia.png  desc={len(desc)} aff_male={aff:.1f} car_fem={car:.1f}")
