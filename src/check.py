import json
import re
import sys
import unicodedata
from collections import defaultdict

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
OUT = r"c:\NetworkScience"


def norm(s):
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z ]", " ", s.lower()).split()


def year(s):
    m = re.search(r"(\d{4})", s or "")
    return int(m.group(1)) if m else None


def full_date(s):

    m = re.match(r"^\s*(\d{1,2})\s+([A-Z]{3})\s+(\d{4})", s or "")
    if m:
        return f"{m.group(2)} {m.group(1)} {m.group(3)}"
    return None


m = json.load(open(rf"{OUT}\royal_updated.json", encoding="utf-8"))
indi, fam = m["individuals"], m["families"]


def num(x):
    return int(re.search(r"\d+", x).group())


def is_new(x):
    return num(x) > 3010


issues = defaultdict(list)


by_key = defaultdict(list)
for x, p in indi.items():
    fd = full_date(p.get("birth_date", ""))
    toks = norm(p.get("name", ""))
    if fd and toks:
        by_key[(toks[0], fd)].append(x)
dup_groups = {k: v for k, v in by_key.items() if len(v) > 1}
cross_dups = {k: v for k, v in dup_groups.items()
              if any(is_new(x) for x in v) and any(not is_new(x) for x in v)}
print(f"[dups] {len(dup_groups)} groups share given-name + exact birth date "
      f"({sum(len(v)-1 for v in dup_groups.values())} redundant nodes)")
print(f"[dups] of those, {len(cross_dups)} pair a NEW node with an EXISTING royal92 "
      f"person (= candidate missed matches)")
for k, v in list(cross_dups.items())[:8]:
    names = [f"{x}:{indi[x]['name'].strip()}" for x in v]
    print(f"        {k[0]} {k[1]}: {names}")


children = defaultdict(list)
parents = defaultdict(list)
for fid, f in fam.items():
    for c in f.get("chil", []):
        for par in (f.get("husb"), f.get("wife")):
            if par and c in indi and par in indi:
                children[par].append(c)
                parents[c].append(par)

bad_age, neg_lifespan, young_parent = 0, 0, 0
for c, pars in parents.items():
    cy = year(indi[c].get("birth_date", ""))
    if cy is None:
        continue
    for par in pars:
        py = year(indi[par].get("birth_date", ""))
        if py is None:
            continue
        gap = cy - py
        if gap < 0:
            bad_age += 1
            if bad_age <= 5:
                issues["parent_after_child"].append(f"{indi[par]['name'].strip()}(b.{py}) -> {indi[c]['name'].strip()}(b.{cy})")
        elif gap < 12:
            young_parent += 1
for x, p in indi.items():
    by, dy = year(p.get("birth_date", "")), year(p.get("death_date", ""))
    if by and dy and dy < by:
        neg_lifespan += 1
print(f"\n[dates] parent born AFTER child: {bad_age}")
print(f"[dates] parent under age 12 at birth: {young_parent}")
print(f"[dates] death before birth: {neg_lifespan}")
for s in issues["parent_after_child"]:
    print(f"        {s}")


self_spouse = sum(1 for f in fam.values() if f.get("husb") and f.get("husb") == f.get("wife"))
self_parent = sum(1 for c, pars in parents.items() if c in pars)
gender_bad = 0
for f in fam.values():
    h, w = f.get("husb"), f.get("wife")
    if h in indi and indi[h].get("sex") == "F" and w in indi and indi[w].get("sex") == "M":
        gender_bad += 1
print(f"\n[struct] self-spouse families: {self_spouse}")
print(f"[struct] person is own parent: {self_parent}")
print(f"[struct] families with husb=Female & wife=Male (role/sex mismatch): {gender_bad}")


def has_cycle():
    color = {}
    def dfs(u, stack):
        color[u] = 1
        for par in parents.get(u, []):
            if color.get(par) == 1:
                return [par]
            if color.get(par) is None:
                r = dfs(par, stack)
                if r:
                    return r
        color[u] = 2
        return None
    for n in list(indi.keys()):
        if color.get(n) is None:
            r = dfs(n, [])
            if r:
                return r
    return None
cyc = has_cycle()
print(f"[struct] ancestry cycle detected: {'YES '+str(cyc) if cyc else 'no'}")


no_sex = sum(1 for p in indi.values() if not p.get("sex"))
no_birth = sum(1 for p in indi.values() if not p.get("birth_date"))
print(f"\n[coverage] missing sex: {no_sex} ({100*no_sex/len(indi):.1f}%)")
print(f"[coverage] missing birth date: {no_birth} ({100*no_birth/len(indi):.1f}%)")


print("\n[spot] known people after expansion:")
def fam_of(x):
    p = indi[x]
    out = []
    for fid in p["fams"]:
        f = fam[fid]
        sp = f["wife"] if f["husb"] == x else f["husb"]
        spn = indi[sp]["name"].strip() if sp in indi else "(none)"
        kids = [indi[c]["given"] for c in f["chil"] if c in indi]
        out.append(f"{spn} -> {kids}")
    return out
for x, who in [("@I52@", "Elizabeth II"), ("@I115@", "William"),
               ("@I116@", "Harry"), ("@I58@", "Charles III"), ("@I1@", "Victoria")]:
    p = indi[x]
    print(f"   {who:<13} b.{p['birth_date']} d.{p['death_date']} | " + " ; ".join(fam_of(x)))
