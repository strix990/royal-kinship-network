import sys
from collections import Counter, defaultdict

import numpy as np
import networkx as nx
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.lines import Line2D

sys.path.insert(0, r"c:\NetworkScience")
import json
import re
from analysis import build_graph, subg_tiers, extract_house

OUT = r"c:\NetworkScience"


def yr(s):
    m = re.search(r"(\d{4})", s or "")
    return int(m.group(1)) if m else None


def build():
    Gall, _ = build_graph(rf"{OUT}\royal_updated.json", "strict", require_titled_parent=True)
    G = subg_tiers(Gall, {"base"})
    G = G.subgraph(max(nx.connected_components(G), key=len)).copy()

    model = json.load(open(rf"{OUT}\royal_updated.json", encoding="utf-8"))
    indi, fam = model["individuals"], model["families"]
    DG = nx.DiGraph()
    DG.add_nodes_from(G.nodes())
    for f in fam.values():
        for parent in (f.get("husb"), f.get("wife")):
            if parent not in G:
                continue
            for c in f.get("chil", []):
                if c in G:
                    DG.add_edge(parent, c)

    for n in G:
        G.nodes[n].setdefault("birth_year", None)
    for _ in range(5):
        for n in G:
            if G.nodes[n]["birth_year"] is None:
                ys = [G.nodes[m]["birth_year"] for m in G.neighbors(n) if G.nodes[m]["birth_year"]]
                if ys:
                    G.nodes[n]["birth_year"] = int(sum(ys) / len(ys))
    return G, DG


def pick_root(DG):
    founders = [n for n in DG if DG.in_degree(n) == 0]
    best, best_n = None, -1
    for f in founders:
        d = len(nx.descendants(DG, f))
        if d > best_n:
            best, best_n = f, d
    return best, best_n


def radial_layout(G, DG, root):
    ST = nx.bfs_tree(DG, root)
    depth = nx.single_source_shortest_path_length(ST, root)
    maxd = max(depth.values())

    dfs_order = list(nx.dfs_preorder_nodes(ST, root))
    leaves = [n for n in dfs_order if ST.out_degree(n) == 0]
    angle = {}
    for i, lf in enumerate(leaves):
        angle[lf] = 2 * np.pi * i / max(len(leaves), 1)
    for n in nx.dfs_postorder_nodes(ST, root):
        ch = list(ST.successors(n))
        if ch:
            angle[n] = float(np.mean([angle[c] for c in ch]))
    pos = {}
    for n in ST:
        r = depth[n] / max(maxd, 1)
        pos[n] = (r * np.cos(angle[n]), r * np.sin(angle[n]))
    return ST, pos, depth, maxd


def main():
    G, DG = build()
    root, ndesc = pick_root(DG)
    ST, pos, depth, maxd = radial_layout(G, DG, root)
    print(f"tree root: {G.nodes[root]['name'].strip()} -> {len(ST)} people on the tree "
          f"({100*len(ST)/G.number_of_nodes():.0f}% of the {G.number_of_nodes()}-node component)")

    comms = sorted(nx.community.louvain_communities(G, seed=42), key=len, reverse=True)
    cof = {n: i for i, c in enumerate(comms) for n in c}
    K = 24
    cmap = plt.cm.turbo(np.linspace(0.05, 0.95, K))
    def color(n):
        c = cof.get(n, K)
        return tuple(cmap[c]) if c < K else (0.45, 0.47, 0.55, 1.0)

    fig, ax = plt.subplots(figsize=(15, 15))
    fig.patch.set_facecolor("#05060d")
    ax.set_facecolor("#05060d")


    segs = [(pos[u], pos[v]) for u, v in ST.edges()]
    cols = [color(v)[:3] + (0.22,) for u, v in ST.edges()]
    ax.add_collection(LineCollection(segs, colors=cols, linewidths=0.35))


    nodes = list(ST.nodes())
    xs = np.array([pos[n][0] for n in nodes])
    ys = np.array([pos[n][1] for n in nodes])
    cs = np.array([color(n) for n in nodes])
    deg = np.array([DG.out_degree(n) for n in nodes])
    s = 5 + 4 * np.sqrt(deg)
    ax.scatter(xs, ys, s=s * 6, c=cs, alpha=0.07, linewidths=0, zorder=2)
    ax.scatter(xs, ys, s=s, c=cs, alpha=0.95, linewidths=0, zorder=3)


    for g in range(1, maxd + 1):
        r = g / maxd
        ax.add_patch(plt.Circle((0, 0), r, fill=False, color="#20242f", lw=0.5, zorder=1))
        ax.text(0, r, f"gen {g}", color="#3c4150", fontsize=6, ha="center", va="bottom", zorder=1)


    famous = ["Victoria  Hanover", "Elizabeth_II", "Henry_VIII", "Maria Theresa  Austria",
              "Louis_XIV", "Charles_II", "George_III", "Christian_IX"]
    name2n = {G.nodes[n]["name"]: n for n in ST}
    for fam in famous:
        hit = next((nm for nm in name2n if fam.lower() in nm.lower()), None)
        if hit:
            x, y = pos[name2n[hit]]
            ax.scatter([x], [y], s=60, facecolors="none", edgecolors="white", linewidths=0.8, zorder=4)
            ax.text(x, y, "  " + hit.replace("_", " ").strip(), color="white", fontsize=7.5,
                    ha="left", va="center", zorder=5, alpha=0.9)

    ax.text(0, 0, G.nodes[root]["name"].replace("_", " ").strip() + " (root)", color="#ffd479",
            fontsize=9, ha="center", va="center", zorder=6)


    handles = []
    for ci in range(min(K, 14)):
        houses = Counter(G.nodes[n]["house"] for n in comms[ci] if G.nodes[n]["house"])
        label = houses.most_common(1)[0][0] if houses else "(mixed)"
        handles.append(Line2D([0], [0], marker="o", linestyle="none", markersize=6,
                              markerfacecolor=cmap[ci], markeredgecolor="none",
                              label=f"{label}"))
    leg = ax.legend(handles=handles, loc="lower left", fontsize=7.5, ncol=2,
                    framealpha=0.0, labelcolor="#d8dbe6", title="largest houses")
    leg.get_title().set_color("#aeb2c2")

    ax.set_xlim(-1.1, 1.1); ax.set_ylim(-1.1, 1.1)
    ax.set_aspect("equal"); ax.axis("off")
    ax.set_title(f"Royal Constellations — descent tree from {G.nodes[root]['name'].strip()} "
                 f"(rings = generations)", color="white", fontsize=15, pad=12)
    fig.savefig(rf"{OUT}\fig_constellation_tree.png", dpi=160, facecolor=fig.get_facecolor())
    print("Wrote fig_constellation_tree.png")


if __name__ == "__main__":
    main()
