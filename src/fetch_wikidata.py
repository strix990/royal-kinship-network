import json
import time
import requests

ENDPOINT = "https://query.wikidata.org/sparql"
HEADERS = {"User-Agent": "RoyalNetworkProject/1.0 (academic course project; contact via course)"}

ROOTS = {
    "Q9439": "Queen Victoria",
    "Q151305": "Christian IX of Denmark",
    "Q170467": "Philip V of Spain",
    "Q131706": "Maria Theresa of Austria",
    "Q7771":   "Louis-Philippe I",
    "Q2079957": "William I of the Netherlands",
    "Q168691": "Victor Emmanuel II of Italy",
    "Q676301": "John VI of Portugal",
    "Q57302":  "Adolphe of Luxembourg",
    "Q159646": "Albert I of Monaco",
}


QUERY = """
SELECT ?p ?pLabel ?birth ?death ?gender ?father ?mother ?spouse WHERE {{
  wd:{root} wdt:P40* ?p .
  OPTIONAL {{ ?p wdt:P569 ?birth }}
  OPTIONAL {{ ?p wdt:P570 ?death }}
  OPTIONAL {{ ?p wdt:P21 ?gender }}
  OPTIONAL {{ ?p wdt:P22 ?father }}
  OPTIONAL {{ ?p wdt:P25 ?mother }}
  OPTIONAL {{ ?p wdt:P26 ?spouse }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
}}
"""


def qid(uri: str):
    return uri.rsplit("/", 1)[-1] if uri else ""


def run_query(root: str, attempts: int = 3):
    last = None
    for i in range(attempts):
        try:
            r = requests.get(
                ENDPOINT,
                params={"query": QUERY.format(root=root), "format": "json"},
                headers=HEADERS,
                timeout=180,
            )
            r.raise_for_status()
            return r.json()["results"]["bindings"]
        except Exception as e:
            last = e
            print(f"    attempt {i+1} failed ({e}); retrying...")
            time.sleep(5 * (i + 1))
    print(f"    GIVING UP on {root}: {last}")
    return []


def main():
    people: dict[str, dict] = {}

    for root, name in ROOTS.items():
        print(f"Querying descendants of {name} ({root}) ...")
        bindings = run_query(root)
        print(f"  {len(bindings)} rows")
        for b in bindings:
            pq = qid(b["p"]["value"])
            rec = people.setdefault(pq, {
                "qid": pq,
                "label": b.get("pLabel", {}).get("value", ""),
                "birth": b.get("birth", {}).get("value", "")[:10],
                "death": b.get("death", {}).get("value", "")[:10],
                "gender": qid(b.get("gender", {}).get("value", "")),
                "fathers": set(),
                "mothers": set(),
                "spouses": set(),
            })
            if not rec["gender"] and "gender" in b:
                rec["gender"] = qid(b["gender"]["value"])
            if "father" in b:
                rec["fathers"].add(qid(b["father"]["value"]))
            if "mother" in b:
                rec["mothers"].add(qid(b["mother"]["value"]))
            if "spouse" in b:
                rec["spouses"].add(qid(b["spouse"]["value"]))
        time.sleep(1)


    out = {}
    for pq, rec in people.items():
        rec = dict(rec)
        rec["fathers"] = sorted(rec["fathers"])
        rec["mothers"] = sorted(rec["mothers"])
        rec["spouses"] = sorted(rec["spouses"])
        out[pq] = rec

    with open(r"c:\NetworkScience\wikidata_people.json", "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)

    print(f"\nTotal unique people: {len(out)}")
    born_after_1980 = sum(1 for r in out.values() if r["birth"][:4].isdigit() and int(r["birth"][:4]) > 1980)
    print(f"Born after 1980 (likely new vs 1992 file): {born_after_1980}")
    print("Wrote wikidata_people.json")


if __name__ == "__main__":
    main()
