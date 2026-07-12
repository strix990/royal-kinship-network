import sys
import networkx as nx

sys.path.insert(0, r"c:\NetworkScience")
from analysis import build_graph

OUT = r"c:\NetworkScience"

G, _ = build_graph(rf"{OUT}\royal_updated.json", "gephi")


for n, d in G.nodes(data=True):
    for k in ("name", "house", "given", "sex", "title", "tier"):
        d[k] = d.get(k) or ""
    d["noble"] = bool(d.get("noble", False))
    d["is_new"] = bool(d.get("is_new", False))
    d["label"] = d["name"]
    for yk in ("birth_year", "death_year"):
        if d.get(yk) is None:
            d.pop(yk, None)
        else:
            d[yk] = int(d[yk])
for u, v, d in G.edges(data=True):
    d["kind"] = d.get("kind", "")

nx.write_gexf(G, rf"{OUT}\royal_network.gexf")
nx.write_graphml(G, rf"{OUT}\royal_network.graphml")
print(f"nodes={G.number_of_nodes()} edges={G.number_of_edges()}")
print("Wrote royal_network.gexf and royal_network.graphml")
