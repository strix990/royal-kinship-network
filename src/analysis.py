import json
import re
import sys
from collections import Counter

import networkx as nx
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = r"c:\NetworkScience"


def year(s):
    m = re.search(r"(\d{4})", s or "")
    return int(m.group(1)) if m else None


PARTICLES = {"von", "zu", "van", "de", "del", "della", "di", "dei", "da", "du",
             "of", "the", "und", "and", "y", "le", "la", "las", "los", "auf",
             "der", "den", "ter", "zur", "of_the", "san", "st"}
TITLE_TOK = {"prinz", "prinzessin", "graf", "grafin", "gräfin", "herzog", "don",
             "dona", "principi", "principe", "principessa", "nobile", "freiherr",
             "freifrau", "baron", "baroness", "count", "countess", "king", "queen",
             "prince", "princess", "duke", "duchess", "archduke", "archduchess",
             "lord", "lady", "sir", "infante", "infanta", "fra"}


def extract_house(raw_name):
    m = re.search(r"/([^/]*)/", raw_name)
    s = (m.group(1) if m else "").replace("_", " ").strip()
    toks = [t for t in s.split()
            if t.lower() not in PARTICLES and t.lower() not in TITLE_TOK
            and t.lower() != "unknown"]
    return " ".join(toks)


def load_noble_map(indi):
    try:
        cross = json.load(open(rf"{OUT}\crosswalk.json", encoding="utf-8"))
        nob = json.load(open(rf"{OUT}\nobility.json", encoding="utf-8"))
    except FileNotFoundError:
        return {x: True for x in indi}
    x2q = {x: q for q, x in cross.items()}
    for x, p in indi.items():
        if p.get("wikidata"):
            x2q[x] = p["wikidata"]
    noble = {}
    for x in indi:
        q = x2q.get(x)
        noble[x] = True if q is None else nob.get(q, {}).get("noble", False)
    return noble


def build_graph(model_path, tag, require_titled_parent=False):
    with open(model_path, encoding="utf-8") as fh:
        m = json.load(fh)
    indi, fam = m["individuals"], m["families"]
    noble = load_noble_map(indi)
    G = nx.Graph()
    for xref, p in indi.items():
        num = int(re.search(r"\d+", xref).group())
        raw = p.get("name", "")
        G.add_node(xref, name=raw.replace("/", " ").strip(),
                   house=extract_house(raw),
                   given=p.get("given", ""), sex=p.get("sex", ""),
                   title=p.get("title", ""), noble=noble.get(xref, True),
                   tier=p.get("tier", "base"),
                   birth_year=year(p.get("birth_date", "")),
                   death_year=year(p.get("death_date", "")),
                   is_new=(num > 3010))
    for fid, f in fam.items():
        h, w = f.get("husb", ""), f.get("wife", "")


        if require_titled_parent:
            parent_titled = (noble.get(h, False) and h in G) or (noble.get(w, False) and w in G)
            if not parent_titled:
                continue
        if h in G and w in G:
            G.add_edge(h, w, kind="spouse")
        for c in f.get("chil", []):
            if c not in G:
                continue
            for parent in (h, w):
                if parent in G:
                    G.add_edge(parent, c, kind="parent")
    if require_titled_parent:
        G.remove_nodes_from([n for n in G if G.degree(n) == 0])
    print(f"[{tag}] nodes={G.number_of_nodes()} edges={G.number_of_edges()}")
    return G, indi


def derive_debloated(Gu):
    G = Gu.copy()
    drop = [(u, v) for u, v, d in G.edges(data=True)
            if d.get("kind") == "spouse" and not G.nodes[u]["noble"] and not G.nodes[v]["noble"]]
    G.remove_edges_from(drop)
    G.remove_nodes_from([n for n in G if G.degree(n) == 0])
    return G


def derive_dedebloated(Gdb):
    G = Gdb.copy()
    while True:
        leaves = [n for n in G if G.degree(n) <= 1 and not G.nodes[n]["noble"]]
        if not leaves:
            break
        G.remove_nodes_from(leaves)
    return G


def derive_noble(Gu):
    return Gu.subgraph([n for n, d in Gu.nodes(data=True) if d["noble"]]).copy()


def subg_tiers(G, tiers):
    return G.subgraph([n for n, d in G.nodes(data=True) if d["tier"] in tiers]).copy()


def global_metrics(G):
    n, e = G.number_of_nodes(), G.number_of_edges()
    comps = list(nx.connected_components(G))
    giant = max(comps, key=len)
    Gc = G.subgraph(giant)
    degs = [d for _, d in G.degree()]
    return {
        "nodes": n, "edges": e,
        "density": nx.density(G),
        "avg_degree": sum(degs) / n,
        "max_degree": max(degs),
        "components": len(comps),
        "giant_frac": len(giant) / n,
        "avg_clustering": nx.average_clustering(G),
        "giant_diameter": nx.diameter(Gc) if len(giant) <= 6000 else None,
        "giant_avg_path": nx.average_shortest_path_length(Gc) if len(giant) <= 4000 else "skipped(>4000)",
    }


def top_central(G, indi, k=12):
    deg = nx.degree_centrality(G)
    btw = nx.betweenness_centrality(G, k=min(800, G.number_of_nodes()), seed=42)
    try:
        eig = nx.eigenvector_centrality(G, max_iter=1000)
    except nx.PowerIterationFailedConvergence:
        eig = {n: 0 for n in G}

    def fmt(scores):
        out = []
        for x, _ in sorted(scores.items(), key=lambda kv: -kv[1])[:k]:
            nm = G.nodes[x]["name"] or indi[x].get("given", x)
            by = G.nodes[x]["birth_year"]
            out.append(f"{nm} (b.{by})")
        return out

    return {"degree": fmt(deg), "betweenness": fmt(btw), "eigenvector": fmt(eig)}


def communities(G, indi):
    comms = nx.community.louvain_communities(G, seed=42, resolution=1.0)
    comms = sorted(comms, key=len, reverse=True)
    deg = dict(G.degree())
    summary = []
    for c in comms[:12]:

        houses = Counter(G.nodes[x]["house"] for x in c if G.nodes[x]["house"])
        top_houses = ", ".join(h for h, _ in houses.most_common(3)) or "(no house / pre-surname)"

        hub = max(c, key=lambda x: deg[x])
        hub_name = G.nodes[hub]["name"]
        hub_year = G.nodes[hub]["birth_year"]
        summary.append((len(c), f"houses: {top_houses}  |  hub: {hub_name} (b.{hub_year})"))
    mod = nx.community.modularity(G, comms)
    return len(comms), mod, summary


def temporal_growth(G):
    years = list(range(1700, 2031, 10))
    sizes = []
    for y in years:
        nodes = [n for n, d in G.nodes(data=True)
                 if d["birth_year"] is None or d["birth_year"] <= y]
        sub = G.subgraph(nodes)
        if sub.number_of_nodes():
            giant = max(nx.connected_components(sub), key=len)
            sizes.append(len(giant))
        else:
            sizes.append(0)
    return years, sizes


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    Go, indi_o = build_graph(rf"{OUT}\royal92_parsed.json", "original")
    Gu_all, indi_u = build_graph(rf"{OUT}\royal_updated.json", "updated(all tiers)")
    Gst_all, _ = build_graph(rf"{OUT}\royal_updated.json", "strict(all tiers)",
                             require_titled_parent=True)

    Gu = subg_tiers(Gu_all, {"base"})
    Gst = subg_tiers(Gst_all, {"base"})
    Gdb = derive_debloated(Gu)
    Gnb = derive_noble(Gu)


    versions = [
        ("original (1992)", Go),
        ("updated (2026)", Gu),
        ("strict-titled", Gst),
    ]

    lines = []
    lines.append("=" * 80)
    lines.append("ROYAL KINSHIP NETWORK -- three-version analysis")
    lines.append("  original      : royal92 as published (1992) -- baseline")
    lines.append("  updated       : + all Wikidata descendants & spouses to 2026 -- full contribution")
    lines.append("  strict-titled : keep a family's edges only if a PARENT is titled -- refined network")
    lines.append("=" * 80)

    metrics = {name: global_metrics(G) for name, G in versions}
    header = f"{'metric':<18}" + "".join(f"{name:>17}" for name, _ in versions)
    lines.append("\n" + header)
    for key in ["nodes", "edges", "density", "avg_degree", "max_degree",
                "components", "giant_frac", "avg_clustering",
                "giant_diameter", "giant_avg_path"]:
        def f(v):
            return f"{v:.4f}" if isinstance(v, float) else str(v)
        row = f"{key:<18}" + "".join(f"{f(metrics[name][key]):>17}" for name, _ in versions)
        lines.append(row)

    new_nodes = sum(1 for _, d in Gu.nodes(data=True) if d["is_new"])
    lines.append(f"\nWikidata additions: {new_nodes} nodes ({100*new_nodes/Gu.number_of_nodes():.1f}% of updated)")


    mdb, mnb = global_metrics(Gdb), global_metrics(Gnb)
    lines.append("\nSide-experiment 1 -- where you cut matters (clustering):")
    lines.append(f"  strict-titled {metrics['strict-titled']['avg_clustering']:.3f}  vs  "
                 f"de-bloated {mdb['avg_clustering']:.3f}  (edge-pruning shatters marriage triangles)")
    lines.append("Side-experiment 2 -- commoners as connective tissue:")
    lines.append(f"  noble-only backbone fragments into {mnb['components']} components "
                 f"(vs {metrics['updated (2026)']['components']} for updated) -> in-laws bridge dynasties")


    for tag, G in [("UPDATED (2026)", Gu), ("STRICT-TITLED", Gst)]:
        lines.append(f"\n--- Centrality leaders [{tag}] ---")
        tc = top_central(G, indi_u)
        for kind, names in tc.items():
            lines.append(f"  Top by {kind}: " + " | ".join(names[:6]))
        ncomm, mod, summ = communities(G, indi_u)
        lines.append(f"--- Communities [{tag}] ---")
        lines.append(f"  {ncomm} communities, modularity = {mod:.3f}; largest:")
        for size, label in summ[:8]:
            lines.append(f"    {size:>5} : {label}")


    Gx_base = subg_tiers(Gst_all, {"base"})
    Gx_bona = subg_tiers(Gst_all, {"base", "bonaparte"})
    ext = [("strict base", Gx_base), ("+ Bonaparte", Gx_bona)]
    lines.append("\n" + "=" * 120)
    lines.append("BONAPARTE EXTENSION (strict-titled filter = the chosen 'best' version)")
    lines.append("  Napoleon's nobility is contested, so Bonaparte is kept as its own toggleable layer.")
    lines.append("=" * 120)
    em = {name: global_metrics(G) for name, G in ext}
    lines.append("\n" + f"{'metric':<18}" + "".join(f"{n:>20}" for n, _ in ext))
    for key in ["nodes", "edges", "components", "giant_frac", "avg_clustering", "max_degree"]:
        def f(v):
            return f"{v:.4f}" if isinstance(v, float) else str(v)
        lines.append(f"{key:<18}" + "".join(f"{f(em[n][key]):>20}" for n, _ in ext))


    members = [n for n, d in Gx_bona.nodes(data=True) if d["tier"] == "bonaparte"]
    giant = max(nx.connected_components(Gx_bona), key=len)
    in_giant = sum(1 for n in members if n in giant)
    lines.append(f"\nBonaparte attachment: {in_giant}/{len(members)} titled Bonaparte nodes "
                 f"({100*in_giant/max(len(members),1):.0f}%) sit inside the European giant component "
                 f"-> married into Europe rather than forming an island.")

    report = "\n".join(lines)
    with open(rf"{OUT}\analysis_report.txt", "w", encoding="utf-8") as fh:
        fh.write(report + "\n")
    print(report)


    plt.figure(figsize=(6.5, 4.5))
    for name, G in versions:
        degs = sorted((d for _, d in G.degree()), reverse=True)
        cnt = Counter(degs)
        xs = sorted(cnt)
        ys = [cnt[x] for x in xs]
        plt.loglog(xs, ys, marker="o", linestyle="none", markersize=3, label=name)
    plt.xlabel("degree k"); plt.ylabel("# nodes")
    plt.title("Degree distribution across versions"); plt.legend(fontsize=8)
    plt.tight_layout(); plt.savefig(rf"{OUT}\fig_degree_distribution.png", dpi=130)
    plt.close()


    yrs, sizes = temporal_growth(Gu)
    plt.figure(figsize=(6, 4))
    plt.plot(yrs, sizes, marker="o", markersize=3)
    plt.xlabel("year (people born up to)"); plt.ylabel("giant component size")
    plt.title("Network growth over time (updated)")
    plt.tight_layout(); plt.savefig(rf"{OUT}\fig_growth.png", dpi=130)
    plt.close()


    names = [n for n, _ in versions]
    fig, ax1 = plt.subplots(figsize=(7, 4.5))
    x = range(len(versions))
    ax1.bar([i - 0.2 for i in x], [metrics[n]["nodes"] for n in names], width=0.4,
            color="steelblue", label="nodes")
    ax1.set_ylabel("nodes", color="steelblue")
    ax1.set_xticks(list(x)); ax1.set_xticklabels(names, rotation=20, ha="right", fontsize=8)
    ax2 = ax1.twinx()
    ax2.plot(list(x), [metrics[n]["avg_clustering"] for n in names], "o-",
             color="darkred", label="avg clustering")
    ax2.set_ylabel("avg clustering", color="darkred")
    plt.title("Network size vs clustering by version")
    plt.tight_layout(); plt.savefig(rf"{OUT}\fig_versions.png", dpi=130)
    plt.close()

    print("\nWrote analysis_report.txt + fig_degree_distribution.png, fig_growth.png, fig_versions.png")


if __name__ == "__main__":
    main()
