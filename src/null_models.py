import sys
import numpy as np
import networkx as nx

sys.path.insert(0, r"c:\NetworkScience")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from analysis import build_graph, subg_tiers

OUT = r"c:\NetworkScience"
rng = np.random.default_rng(42)


def sampled_apl(G, nsamp=400):
    giant = G.subgraph(max(nx.connected_components(G), key=len))
    nodes = list(giant.nodes())
    src = rng.choice(len(nodes), size=min(nsamp, len(nodes)), replace=False)
    tot, cnt = 0, 0
    for i in src:
        lengths = nx.single_source_shortest_path_length(giant, nodes[i])
        tot += sum(lengths.values())
        cnt += len(lengths) - 1
    return tot / cnt


def degree_stats(G):
    d = np.array([k for _, k in G.degree()], dtype=float)
    return d.mean(), int(d.max()), d.std() / d.mean()


def analyze(name, G):
    n, m = G.number_of_nodes(), G.number_of_edges()
    kmean, kmax, cv = degree_stats(G)
    C = nx.average_clustering(G)
    L = sampled_apl(G)


    ER = nx.gnm_random_graph(n, m, seed=42)
    C_er = nx.average_clustering(ER)
    L_er = sampled_apl(ER)
    _, kmax_er, cv_er = degree_stats(ER)


    m_ba = max(1, round(m / n))
    BA = nx.barabasi_albert_graph(n, m_ba, seed=42)
    _, kmax_ba, cv_ba = degree_stats(BA)

    sigma = (C / C_er) / (L / L_er) if C_er > 0 and L_er > 0 else float("nan")

    print(f"\n=== {name}  (n={n}, m={m}, <k>={kmean:.2f}) ===")
    print(f"  clustering   C={C:.3f}   C_ER={C_er:.4f}   ratio C/C_ER={C/C_er:.0f}x")
    print(f"  avg path     L={L:.2f}    L_ER={L_er:.2f}    ratio L/L_ER={L/L_er:.2f}x")
    print(f"  small-world  sigma=(C/C_ER)/(L/L_ER)={sigma:.1f}   "
          f"(short paths? {'yes' if L/L_er < 1.5 else 'NO -> large-world'})")
    print(f"  degree tail  kmax={kmax}  CV={cv:.2f}    | ER kmax={kmax_er} CV={cv_er:.2f}"
          f"  | BA kmax={kmax_ba} CV={cv_ba:.2f}")
    return dict(name=name, n=n, m=m, kmean=kmean, kmax=kmax, cv=cv, C=C, C_er=C_er,
                L=L, L_er=L_er, sigma=sigma, kmax_ba=kmax_ba, cv_ba=cv_ba)


def main():
    Go, _ = build_graph(rf"{OUT}\royal92_parsed.json", "original")
    Gu_all, _ = build_graph(rf"{OUT}\royal_updated.json", "updated")
    Gst_all, _ = build_graph(rf"{OUT}\royal_updated.json", "strict", require_titled_parent=True)
    Gu = subg_tiers(Gu_all, {"base"})
    Gst = subg_tiers(Gst_all, {"base"})
    rows = [analyze("original (1992)", Go),
            analyze("updated (2026)", Gu),
            analyze("strict-titled", Gst)]


    print("\n% ---- LaTeX rows (empirical vs ER) ----")
    for r in rows:
        print(f"{r['name']} & {r['C']:.3f} & {r['C_er']:.4f} & {r['L']:.1f} & "
              f"{r['L_er']:.1f} & {r['sigma']:.0f} & {r['kmax']} & {r['kmax_ba']} \\\\")


if __name__ == "__main__":
    main()
