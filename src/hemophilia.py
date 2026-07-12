import json
import re
import sys
from collections import defaultdict

sys.path.insert(0, r"c:\NetworkScience")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

OUT = r"c:\NetworkScience"
model = json.load(open(rf"{OUT}\royal_updated.json", encoding="utf-8"))
indi, fam = model["individuals"], model["families"]


def yr(s):
    m = re.search(r"(\d{4})", s or "")
    return int(m.group(1)) if m else 3000


father, mother, children = {}, {}, defaultdict(list)
for f in fam.values():
    h, w = f.get("husb"), f.get("wife")
    for c in f.get("chil", []):
        if h:
            father[c] = h; children[h].append(c)
        if w:
            mother[c] = w; children[w].append(c)

VICTORIA = "@I1@"
assert indi[VICTORIA]["sex"] == "F", indi[VICTORIA]["name"]


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

aff_male = sum(p for v, p in e.items() if v != VICTORIA and indi[v]["sex"] == "M")
car_fem = sum(p for v, p in e.items() if v != VICTORIA and indi[v]["sex"] == "F")
reached = sum(1 for v, p in e.items() if p > 0.001)
print(f"Victoria's descendants processed: {len(desc)}")
print(f"expected affected males:  {aff_male:.1f}")
print(f"expected carrier females: {car_fem:.1f}")
print(f"individuals with non-negligible allele probability: {reached}")

print("\nHighest carrier/affected probabilities (name, sex, birth, P):")
top = sorted(((p, v) for v, p in e.items() if v != VICTORIA), reverse=True)[:18]
for p, v in top:
    nm = indi[v]["name"].replace("/", " ").strip()
    print(f"  {p:.3f}  {indi[v]['sex']}  b.{yr(indi[v].get('birth_date','')):<4}  {nm}")
