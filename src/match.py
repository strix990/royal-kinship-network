import json
import re
import unicodedata


HONORIFICS = {
    "prince", "princess", "prinz", "prinzessin", "principe", "principessa",
    "king", "queen", "duke", "duchess", "lord", "lady", "sir", "dame",
    "archduke", "archduchess", "grand", "infante", "infanta", "count",
    "countess", "baron", "baroness", "freiherr", "freifrau", "graf", "grafin",
    "nobile", "don", "dona", "the", "of", "st",
}

STOP = {"i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x",
        "xi", "xii", "xiii", "jr", "sr"}


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z ]", " ", s.lower()).strip()


def name_tokens(name: str) -> list:
    toks = [t for t in norm(name).split() if t not in HONORIFICS and t not in STOP]
    return toks


def first_token(name: str) -> str:
    toks = name_tokens(name)
    return toks[0] if toks else ""


def tokens(name: str) -> set:
    return set(name_tokens(name))


def year(s: str):
    m = re.search(r"(\d{4})", s or "")
    return int(m.group(1)) if m else None


_MONTHS = {m: i for i, m in enumerate(
    ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"], 1)}


def full_date_ged(s: str):
    if not s or re.search(r"ABT|BEF|AFT|EST|BET", s):
        return None
    m = re.match(r"^\s*(\d{1,2})\s+([A-Z]{3})\s+(\d{4})\s*$", s.strip())
    if m and m.group(2) in _MONTHS:
        return (int(m.group(3)), _MONTHS[m.group(2)], int(m.group(1)))
    return None


def full_date_iso(s: str):
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", s or "")
    if m:
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if mo and d:
            return (y, mo, d)
    return None


def main():
    with open(r"c:\NetworkScience\royal92_parsed.json", encoding="utf-8") as fh:
        r92 = json.load(fh)
    with open(r"c:\NetworkScience\wikidata_people.json", encoding="utf-8") as fh:
        wd = json.load(fh)

    indi = r92["individuals"]


    by_year: dict[int, list] = {}
    by_date: dict[tuple, list] = {}
    for xref, rec in indi.items():
        y = year(rec.get("birth_date", ""))
        if y is not None:
            by_year.setdefault(y, []).append(xref)
        fd = full_date_ged(rec.get("birth_date", ""))
        if fd is not None:
            by_date.setdefault(fd, []).append(xref)

    crosswalk = {}
    matched_xrefs = set()
    new_people = []
    date_matches = 0


    name_candidates = []
    for qid, rec in wd.items():
        wy = year(rec.get("birth", ""))
        wtokens = tokens(rec.get("label", ""))
        wfirst = first_token(rec.get("label", ""))
        wfd = full_date_iso(rec.get("birth", ""))
        if wy is None or not wfirst:
            continue
        cands = []
        for dy in (wy, wy - 1, wy + 1):
            cands.extend(by_year.get(dy, []))
        for xref in cands:
            rt = tokens(indi[xref].get("name", ""))
            rfirst = first_token(indi[xref].get("name", ""))
            if wfirst != rfirst:
                continue
            score = len(wtokens & rt) + 2


            rfd = full_date_ged(indi[xref].get("birth_date", ""))
            if wfd is not None and wfd == rfd:
                score += 10
            name_candidates.append((score, qid, xref))

    for score, qid, xref in sorted(name_candidates, key=lambda t: -t[0]):
        if qid in crosswalk or xref in matched_xrefs:
            continue
        crosswalk[qid] = xref
        matched_xrefs.add(xref)


    for qid, rec in wd.items():
        if qid in crosswalk:
            continue
        wd_fd = full_date_iso(rec.get("birth", ""))
        if wd_fd is not None:
            cands = [x for x in by_date.get(wd_fd, []) if x not in matched_xrefs]
            if len(cands) == 1:
                crosswalk[qid] = cands[0]
                matched_xrefs.add(cands[0])
                date_matches += 1

    for qid, rec in wd.items():
        if qid not in crosswalk:
            new_people.append(rec)

    with open(r"c:\NetworkScience\crosswalk.json", "w", encoding="utf-8") as fh:
        json.dump(crosswalk, fh, ensure_ascii=False, indent=1)
    with open(r"c:\NetworkScience\new_people.json", "w", encoding="utf-8") as fh:
        json.dump(new_people, fh, ensure_ascii=False, indent=1)

    print(f"Wikidata people total:        {len(wd)}")
    print(f"  matched to existing royal92: {len(crosswalk)}")
    print(f"    (of which rescued by exact-date despite name mismatch: {date_matches})")
    print(f"  NEW (not in royal92):        {len(new_people)}")
    new_after_1980 = sum(1 for r in new_people if year(r.get('birth','')) and year(r.get('birth','')) > 1980)
    new_no_year = sum(1 for r in new_people if year(r.get('birth','')) is None)
    print(f"    of which born after 1980:  {new_after_1980}")
    print(f"    of which no birth year:    {new_no_year}")


    anchors = {
        "Q9682": "Elizabeth II (b.1926)", "Q43274": "Charles III (b.1948)",
        "Q9685": "Diana (b.1961)", "Q36812": "William (b.1982)",
        "Q152316": "Harry (b.1984)", "Q80976": "Philip (b.1921)",
        "Q9439": "Victoria (root, b.1819)",
    }
    print("\nAnchor check (existing royals -> should map to a royal92 xref):")
    for q, desc in anchors.items():
        if q in crosswalk:
            xref = crosswalk[q]
            print(f"  {desc:<28} -> {xref}  {indi[xref]['name']}")
        elif q in wd:
            print(f"  {desc:<28} -> NEW (no match){'  <-- check' if year(wd[q].get('birth','')) and year(wd[q]['birth'])<1992 else ''}")
        else:
            print(f"  {desc:<28} -> not in fetched set")


    print("\nExamples of new people born after 2000:")
    shown = 0
    for r in sorted(new_people, key=lambda x: x.get('birth','')):
        y = year(r.get('birth',''))
        if y and y > 2000:
            print(f"  {r['label']:<35} b.{r['birth']}  ({r['qid']})")
            shown += 1
            if shown >= 12:
                break


if __name__ == "__main__":
    main()
