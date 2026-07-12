import json
import time
import requests

ENDPOINT = "https://query.wikidata.org/sparql"
HEADERS = {"User-Agent": "RoyalNetworkProject/1.0 (academic course project)"}
ROOTS = ["Q9439", "Q151305", "Q170467", "Q131706", "Q7771",
         "Q2079957", "Q168691", "Q676301", "Q57302", "Q159646",
         "Q151869"]


NON_BLOOD = ("adopt", "foster", "step")


def qid(uri):
    return uri.rsplit("/", 1)[-1] if uri else ""


def main():
    edges = set()
    for r in ROOTS:
        q = f"""SELECT ?parent ?child ?kinLabel WHERE {{
          wd:{r} wdt:P40* ?parent. ?parent p:P40 ?st. ?st ps:P40 ?child.
          ?st pq:P1039 ?kin.
          SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }} }}"""
        b = requests.get(ENDPOINT, params={"query": q, "format": "json"},
                         headers=HEADERS, timeout=180).json()["results"]["bindings"]
        for row in b:
            kl = row["kinLabel"]["value"].lower()
            if any(k in kl for k in NON_BLOOD):
                edges.add((qid(row["parent"]["value"]), qid(row["child"]["value"])))
        time.sleep(1)

    out = sorted(edges)
    with open(r"c:\NetworkScience\adoptive_edges.json", "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print(f"Non-blood (adopted/foster/step) parent-child links found: {len(out)}")
    for p, c in out:
        print(f"  {p} -> {c}")


if __name__ == "__main__":
    main()
