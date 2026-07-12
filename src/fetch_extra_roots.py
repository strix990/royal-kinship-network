import json
import time
import requests

ENDPOINT = "https://query.wikidata.org/sparql"
HEADERS = {"User-Agent": "RoyalNetworkProject/1.0 (academic course project)"}
EXTRA = [("Q151869", "bonaparte")]

CLOSURE = """
SELECT ?p ?pLabel ?birth ?death ?gender ?father ?mother ?spouse WHERE {{
  wd:{root} wdt:P40* ?p .
  OPTIONAL {{ ?p wdt:P569 ?birth }}
  OPTIONAL {{ ?p wdt:P570 ?death }}
  OPTIONAL {{ ?p wdt:P21 ?gender }}
  OPTIONAL {{ ?p wdt:P22 ?father }}
  OPTIONAL {{ ?p wdt:P25 ?mother }}
  OPTIONAL {{ ?p wdt:P26 ?spouse }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
}}"""


def qid(uri):
    return uri.rsplit("/", 1)[-1] if uri else ""


def get(query):
    r = requests.get(ENDPOINT, params={"query": query, "format": "json"},
                     headers=HEADERS, timeout=180)
    r.raise_for_status()
    return r.json()["results"]["bindings"]


def main():
    with open(r"c:\NetworkScience\wikidata_people.json", encoding="utf-8") as fh:
        people = json.load(fh)
    base_keys = set(people.keys())
    for rec in people.values():
        rec["tier"] = "base"

    for root, tier in EXTRA:
        print(f"Fetching {tier} closure ({root}) ...")
        rows = get(CLOSURE.format(root=root))
        for b in rows:
            pq = qid(b["p"]["value"])
            rec = people.setdefault(pq, {
                "qid": pq, "label": b.get("pLabel", {}).get("value", ""),
                "birth": b.get("birth", {}).get("value", "")[:10],
                "death": b.get("death", {}).get("value", "")[:10],
                "gender": qid(b.get("gender", {}).get("value", "")),
                "fathers": set(), "mothers": set(), "spouses": set(),
                "tier": ("base" if pq in base_keys else tier),
            })
            for k in ("fathers", "mothers", "spouses"):
                if isinstance(rec[k], list):
                    rec[k] = set(rec[k])
            if "father" in b:
                rec["fathers"].add(qid(b["father"]["value"]))
            if "mother" in b:
                rec["mothers"].add(qid(b["mother"]["value"]))
            if "spouse" in b:
                rec["spouses"].add(qid(b["spouse"]["value"]))
        time.sleep(1)


    referenced = {}
    for rec in people.values():
        if rec.get("tier") == "base":
            continue
        for k in ("fathers", "mothers", "spouses"):
            vals = rec[k] if isinstance(rec[k], set) else set(rec[k])
            for v in vals:
                if v not in people:
                    referenced.setdefault(v, rec["tier"])
    missing = sorted(referenced)
    print(f"Fetching {len(missing)} married-in/external nodes for the extensions ...")
    for i in range(0, len(missing), 200):
        chunk = missing[i:i + 200]
        vals = " ".join(f"wd:{q}" for q in chunk)
        rows = get(f"""SELECT ?p ?pLabel ?birth ?death ?gender WHERE {{
          VALUES ?p {{ {vals} }}
          OPTIONAL {{ ?p wdt:P569 ?birth }} OPTIONAL {{ ?p wdt:P570 ?death }}
          OPTIONAL {{ ?p wdt:P21 ?gender }}
          SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }} }}""")
        for b in rows:
            pq = qid(b["p"]["value"])
            if pq in people:
                continue
            people[pq] = {
                "qid": pq, "label": b.get("pLabel", {}).get("value", ""),
                "birth": b.get("birth", {}).get("value", "")[:10],
                "death": b.get("death", {}).get("value", "")[:10],
                "gender": qid(b.get("gender", {}).get("value", "")),
                "fathers": set(), "mothers": set(), "spouses": set(),
                "tier": referenced[pq],
            }
        time.sleep(0.5)


    out = {}
    for pq, rec in people.items():
        rec = dict(rec)
        for k in ("fathers", "mothers", "spouses"):
            rec[k] = sorted(rec[k]) if isinstance(rec[k], set) else sorted(rec[k])
        out[pq] = rec
    with open(r"c:\NetworkScience\wikidata_people.json", "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)

    from collections import Counter
    tiers = Counter(r["tier"] for r in out.values())
    print(f"\nTotal people: {len(out)}  tiers: {dict(tiers)}")


if __name__ == "__main__":
    main()
