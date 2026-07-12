import json
import re

MONTHS = ["", "JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP",
          "OCT", "NOV", "DEC"]
MALE, FEMALE = "Q6581097", "Q6581072"


def gyear(s):
    m = re.search(r"(\d{4})", s or "")
    return int(m.group(1)) if m else None


def iso_to_ged(iso: str) -> str:
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", iso or "")
    if not m:
        return ""
    y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if mo and d:
        return f"{d:02d} {MONTHS[mo]} {y}"
    return str(y)


LEADING_TITLES = {
    "prince", "princess", "king", "queen", "duke", "duchess", "archduke",
    "archduchess", "lord", "lady", "sir", "dame", "count", "countess", "baron",
    "baroness", "infante", "infanta", "don", "dona", "grand",
}


def clean_name(label: str):
    label = re.split(r",", label.strip())[0].strip()
    words = label.split()
    title_words = []
    while words and words[0].lower() in LEADING_TITLES:
        title_words.append(words.pop(0))
    rest = " ".join(words)
    title = " ".join(title_words)

    m = re.match(r"^(.*?)\s+of\s+(.+)$", rest)
    if m:
        name = f"{m.group(1).strip()} /{m.group(2).strip()}/"
    else:
        name = f"{rest} //"
    return name, title


def main():
    with open(r"c:\NetworkScience\royal92_parsed.json", encoding="utf-8") as fh:
        data = json.load(fh)
    with open(r"c:\NetworkScience\wikidata_people.json", encoding="utf-8") as fh:
        wd = json.load(fh)
    with open(r"c:\NetworkScience\crosswalk.json", encoding="utf-8") as fh:
        crosswalk = json.load(fh)
    with open(r"c:\NetworkScience\adoptive_edges.json", encoding="utf-8") as fh:
        adoptive_qid_edges = {tuple(e) for e in json.load(fh)}

    indi = data["individuals"]
    fam = data["families"]


    max_i = max(int(re.search(r"\d+", k).group()) for k in indi)
    max_f = max(int(re.search(r"\d+", k).group()) for k in fam)
    next_i, next_f = max_i + 1, max_f + 1

    qid2xref = dict(crosswalk)
    new_xrefs = set()
    new_count = 0
    for qid, rec in wd.items():
        if qid in qid2xref:
            continue
        xref = f"@I{next_i}@"
        next_i += 1
        sex = "M" if rec["gender"] == MALE else "F" if rec["gender"] == FEMALE else ""
        name, title = clean_name(rec["label"])
        indi[xref] = {
            "xref": xref, "name": name,
            "given": re.split(r",", rec["label"])[0].strip(), "surname": "",
            "sex": sex, "title": title,
            "birth_date": iso_to_ged(rec["birth"]), "birth_place": "",
            "chr_date": "", "death_date": iso_to_ged(rec["death"]), "death_place": "",
            "buri_place": "", "refn": "", "fams": [], "famc": "",
            "wikidata": qid, "tier": rec.get("tier", "base"),
        }
        qid2xref[qid] = xref
        new_xrefs.add(xref)
        new_count += 1

    def is_new(x):
        return x in new_xrefs


    parent_groups: dict[tuple, set] = {}
    spouse_pairs: set = set()
    for qid, rec in wd.items():
        cx = qid2xref[qid]
        fxs = [qid2xref[f] for f in rec["fathers"] if f in qid2xref]
        mxs = [qid2xref[m] for m in rec["mothers"] if m in qid2xref]
        fx = fxs[0] if fxs else ""
        mx = mxs[0] if mxs else ""
        if fx or mx:
            parent_groups.setdefault((fx, mx), set()).add(cx)
        for s in rec["spouses"]:
            if s in qid2xref:
                spouse_pairs.add(frozenset((cx, qid2xref[s])))


    pair_to_fam: dict[frozenset, str] = {}
    for fid, f in fam.items():
        if f["husb"] or f["wife"]:
            pair_to_fam[frozenset(x for x in (f["husb"], f["wife"]) if x)] = fid

    def set_famc(child, fid):
        indi[child]["famc"] = fid

    def add_fams(parent, fid):
        if parent and fid not in indi[parent]["fams"]:
            indi[parent]["fams"].append(fid)

    fams_added = 0
    children_appended = 0


    for (fx, mx), kids in parent_groups.items():
        pair = frozenset(x for x in (fx, mx) if x)
        existing_fid = pair_to_fam.get(pair) if pair else None

        involves_new = is_new(fx) or is_new(mx) or any(is_new(k) for k in kids)
        if existing_fid:

            f = fam[existing_fid]
            for k in kids:
                if k not in f["chil"]:
                    f["chil"].append(k)
                    set_famc(k, existing_fid)
                    children_appended += 1
            continue
        if not involves_new:
            continue
        fid = f"@F{next_f}@"
        next_f += 1

        husb, wife = fx, mx
        new_fam = {"xref": fid, "husb": husb, "wife": wife, "chil": sorted(kids),
                   "marr_date": "", "marr_place": "", "divorced": False, "wikidata": True}
        fam[fid] = new_fam
        pair_to_fam[pair] = fid
        add_fams(husb, fid)
        add_fams(wife, fid)
        for k in kids:
            set_famc(k, fid)
        fams_added += 1


    for pair in spouse_pairs:
        if pair in pair_to_fam:
            continue
        a, b = tuple(pair) if len(pair) == 2 else (next(iter(pair)), "")
        if not (is_new(a) or is_new(b)):
            continue

        sa, sb = indi[a]["sex"], indi[b]["sex"] if b else ""
        if sa == "F" or sb == "M":
            husb, wife = b, a
        else:
            husb, wife = a, b
        fid = f"@F{next_f}@"
        next_f += 1
        fam[fid] = {"xref": fid, "husb": husb, "wife": wife, "chil": [],
                    "marr_date": "", "marr_place": "", "divorced": False, "wikidata": True}
        pair_to_fam[pair] = fid
        add_fams(husb, fid)
        add_fams(wife, fid)
        fams_added += 1


    for p in indi.values():
        p.setdefault("tier", "base")
    for q, xref in qid2xref.items():
        indi[xref]["tier"] = wd[q].get("tier", "base")


    deaths_filled = 0
    for qid, xref in crosswalk.items():
        wdeath = iso_to_ged(wd[qid]["death"])
        if wdeath and not indi[xref].get("death_date"):
            indi[xref]["death_date"] = wdeath
            indi[xref]["death_filled_from_wd"] = qid
            deaths_filled += 1


    adoptive_xref = set()
    for pq, cq in adoptive_qid_edges:
        if pq in qid2xref and cq in qid2xref:
            adoptive_xref.add((qid2xref[pq], qid2xref[cq]))

    removed_adopt, removed_baddate, deaths_cleared = 0, 0, 0
    for fid, f in fam.items():
        h, w = f.get("husb", ""), f.get("wife", "")
        keep = []
        for c in f.get("chil", []):

            if (h, c) in adoptive_xref or (w, c) in adoptive_xref:
                removed_adopt += 1
                if indi.get(c, {}).get("famc") == fid:
                    indi[c]["famc"] = ""
                continue

            cy = gyear(indi.get(c, {}).get("birth_date", ""))
            bad = False
            if cy is not None:
                for par in (h, w):
                    py = gyear(indi.get(par, {}).get("birth_date", "")) if par else None
                    if py is not None and cy - py < 12:
                        bad = True
                        break
            if bad:
                removed_baddate += 1
                if indi.get(c, {}).get("famc") == fid:
                    indi[c]["famc"] = ""
                continue
            keep.append(c)
        f["chil"] = keep

    for p in indi.values():
        by, dy = gyear(p.get("birth_date", "")), gyear(p.get("death_date", ""))
        if by and dy and dy < by:
            p["death_date"] = ""
            deaths_cleared += 1


    write_gedcom(indi, fam, r"c:\NetworkScience\royal_updated.ged")
    print(f"Pruned non-blood (adopted/foster) child links: {removed_adopt}")
    print(f"Pruned impossible-date child links:            {removed_baddate}")
    print(f"Cleared death-before-birth dates:              {deaths_cleared}")

    print(f"New individuals added:     {new_count}")
    print(f"New families created:      {fams_added}")
    print(f"Children appended to existing families: {children_appended}")
    print(f"Death dates filled from Wikidata:       {deaths_filled}")
    print(f"TOTAL individuals: {len(indi)}  (was {len(data['individuals']) if False else max_i})")
    print(f"TOTAL families:    {len(fam)}")
    print("Wrote royal_updated.ged")


    with open(r"c:\NetworkScience\royal_updated.json", "w", encoding="utf-8") as fh:
        json.dump({"individuals": indi, "families": fam}, fh, ensure_ascii=False, indent=1)


def write_gedcom(indi, fam, path):
    L = []
    L.append("0 HEAD")
    L.append("1 SOUR RoyalNetworkProject")
    L.append("2 NAME royal92 augmented with Wikidata (2026)")
    L.append("1 GEDC")
    L.append("2 VERS 5.5.1")
    L.append("1 CHAR UTF-8")
    for xref, p in indi.items():
        L.append(f"0 {xref} INDI")
        L.append(f"1 NAME {p['name']}")
        if p.get("sex"):
            L.append(f"1 SEX {p['sex']}")
        if p.get("title"):
            L.append(f"1 TITL {p['title']}")
        if p.get("birth_date") or p.get("birth_place"):
            L.append("1 BIRT")
            if p.get("birth_date"):
                L.append(f"2 DATE {p['birth_date']}")
            if p.get("birth_place"):
                L.append(f"2 PLAC {p['birth_place']}")
        if p.get("chr_date"):
            L.append("1 CHR")
            L.append(f"2 DATE {p['chr_date']}")
        if p.get("death_date") or p.get("death_place"):
            L.append("1 DEAT")
            if p.get("death_date"):
                L.append(f"2 DATE {p['death_date']}")
            if p.get("death_place"):
                L.append(f"2 PLAC {p['death_place']}")
        if p.get("buri_place"):
            L.append("1 BURI")
            L.append(f"2 PLAC {p['buri_place']}")
        if p.get("refn"):
            L.append(f"1 REFN {p['refn']}")
        for fs in p.get("fams", []):
            L.append(f"1 FAMS {fs}")
        if p.get("famc"):
            L.append(f"1 FAMC {p['famc']}")
        if p.get("wikidata"):
            L.append(f"1 NOTE Wikidata:{p['wikidata']}")
        elif p.get("death_filled_from_wd"):
            L.append(f"1 NOTE DeathFromWikidata:{p['death_filled_from_wd']}")
    for fid, f in fam.items():
        L.append(f"0 {fid} FAM")
        if f.get("husb"):
            L.append(f"1 HUSB {f['husb']}")
        if f.get("wife"):
            L.append(f"1 WIFE {f['wife']}")
        for c in f.get("chil", []):
            L.append(f"1 CHIL {c}")
        if f.get("marr_date") or f.get("marr_place"):
            L.append("1 MARR")
            if f.get("marr_date"):
                L.append(f"2 DATE {f['marr_date']}")
            if f.get("marr_place"):
                L.append(f"2 PLAC {f['marr_place']}")
        if f.get("divorced"):
            L.append("1 DIV Y")
        if f.get("wikidata"):
            L.append("1 NOTE Source:Wikidata")
    L.append("0 TRLR")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
