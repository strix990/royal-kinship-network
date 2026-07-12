import sys
import numpy as np
import networkx as nx
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, r"c:\NetworkScience")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from analysis import build_graph, subg_tiers

OUT = r"c:\NetworkScience"
Gst_all, _ = build_graph(rf"{OUT}\royal_updated.json", "strict", require_titled_parent=True)
G = subg_tiers(Gst_all, {"base"})
comms = sorted(nx.community.louvain_communities(G, seed=42, resolution=1.0),
               key=len, reverse=True)


def find(substr):
    for c in comms:
        if any(substr.lower() in G.nodes[x]["name"].lower() for x in c):
            return set(c)
    return set()


A = find("Woodville")
B = find("Edward_I ")
ext = {v for u in (A | B) for v in G.neighbors(u) if v not in A and v not in B}
H = G.subgraph(A | B | ext)


init = {}
for n in H:
    if n in A:
        init[n] = np.array([-1.6, 0.0]) + 0.25 * np.random.RandomState(hash(n) & 7).randn(2)
    elif n in B:
        init[n] = np.array([1.6, 0.0]) + 0.25 * np.random.RandomState(hash(n) & 7).randn(2)
    else:
        init[n] = np.array([0.0, 0.0]) + 0.1 * np.random.RandomState(hash(n) & 7).randn(2)
pos = nx.spring_layout(H, pos=init, k=0.10, iterations=120, seed=1)

fig, ax = plt.subplots(figsize=(11, 7.5))
fig.patch.set_facecolor("#0d0b14")
ax.set_facecolor("#0d0b14")

C_A, C_B, C_EXT, C_BRIDGE = "#e0567a", "#4aa8d8", "#6b6478", "#ffd36b"


def draw_edges(edgelist, color, lw, alpha):
    segs = [[pos[u], pos[v]] for u, v in edgelist]
    from matplotlib.collections import LineCollection
    ax.add_collection(LineCollection(segs, colors=color, linewidths=lw, alpha=alpha))


internalA = [(u, v) for u, v in H.edges() if u in A and v in A]
internalB = [(u, v) for u, v in H.edges() if u in B and v in B]
bridges = [(u, v) for u, v in H.edges()
           if ((u in A or u in B) and v in ext) or ((v in A or v in B) and u in ext)
           or (u in A and v in B) or (u in B and v in A)]
draw_edges(internalA, C_A, 0.5, 0.5)
draw_edges(internalB, C_B, 0.5, 0.5)
draw_edges(bridges, C_BRIDGE, 1.6, 0.95)

for group, col, sz in [(ext, C_EXT, 12), (A, C_A, 34), (B, C_B, 34)]:
    xs = [pos[n][0] for n in group]
    ys = [pos[n][1] for n in group]
    ax.scatter(xs, ys, s=sz, c=col, linewidths=0, alpha=0.9, zorder=3)


for grp, key, txt in [(A, "Woodville", "Elizabeth Woodville\n(Wars of the Roses)"),
                      (B, "Edward_I ", "Edward I\n(Scottish claimants)")]:
    hub = max(grp, key=lambda x: G.degree(x))
    ax.annotate(txt, pos[hub], textcoords="offset points", xytext=(6, 6),
                fontsize=10, color="#f2eede", fontweight="bold",
                ha="left", va="bottom")

from matplotlib.lines import Line2D
legend = [Line2D([0], [0], marker="o", color="none", markerfacecolor=C_A,
                 markersize=9, label=f"Wars of the Roses  ({len(A)} nodes)"),
          Line2D([0], [0], marker="o", color="none", markerfacecolor=C_B,
                 markersize=9, label=f"Scottish claimants  ({len(B)} nodes)"),
          Line2D([0], [0], marker="o", color="none", markerfacecolor=C_EXT,
                 markersize=7, label="rest of graph (bridge partners)"),
          Line2D([0], [0], color=C_BRIDGE, lw=2,
                 label=f"bridge marriages ({len(bridges)} to the rest)")]
leg = ax.legend(handles=legend, loc="lower center", ncol=2, frameon=False,
                fontsize=9, labelcolor="#e8e2f0", bbox_to_anchor=(0.5, -0.02))

ax.set_title("Two near-isolated medieval communities: dense within, joined to the "
             "15{,}000-node network by a handful of marriages".replace("{,}", ","),
             color="#ece8f2", fontsize=12, pad=12)
ax.axis("off")
fig.tight_layout()
fig.savefig(rf"{OUT}\fig_endogamy.png", dpi=200, bbox_inches="tight",
            facecolor=fig.get_facecolor())
nb = len(bridges)
print(f"Wrote fig_endogamy.png  A={len(A)} B={len(B)} ext={len(ext)} bridges={nb}")
