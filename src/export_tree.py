import json
import re
from collections import defaultdict

OUT = r"c:\NetworkScience"
m = json.load(open(rf"{OUT}\royal_updated.json", encoding="utf-8"))
indi, fam = m["individuals"], m["families"]


def yr(s):
    g = re.search(r"(\d{4})", s or "")
    return g.group(1) if g else ""


def clean(x):
    return indi[x]["name"].replace("/", " ").replace("_", " ").strip()


children = defaultdict(list)
spouses = defaultdict(list)
for f in fam.values():
    h, w = f.get("husb"), f.get("wife")
    if h and w:
        spouses[h].append(w); spouses[w].append(h)
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


def build(x, seen):
    seen.add(x)
    node = {"n": clean(x)}
    y1, y2 = yr(indi[x].get("birth_date", "")), yr(indi[x].get("death_date", ""))
    if y1 or y2:
        node["y"] = f"{y1}–{y2}" if y2 else f"b.{y1}" if y1 else ""
    sp = sorted({clean(s) for s in spouses.get(x, []) if s in indi})
    if sp:
        node["s"] = ", ".join(sp[:3])
    kids = [c for c in children.get(x, []) if c in indi and c not in seen]
    if kids:
        node["c"] = [build(c, seen) for c in kids]
    return node


tree = build(root, set())
n_nodes = best_n + 1
with open(rf"{OUT}\tree_data.js", "w", encoding="utf-8") as fh:
    fh.write("const TREE_DATA = ")
    json.dump(tree, fh, ensure_ascii=False, separators=(",", ":"))
    fh.write(";\n")
print(f"Wrote tree_data.js ({n_nodes} nodes)")
