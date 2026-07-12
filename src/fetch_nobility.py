import json
import time
import requests

ENDPOINT = "https://query.wikidata.org/sparql"
HEADERS = {"User-Agent": "RoyalNetworkProject/1.0 (academic course project)"}


def main():
    with open(r"c:\NetworkScience\wikidata_people.json", encoding="utf-8") as fh:
        people = json.load(fh)
    qids = list(people.keys())
    nobility = {}

    for i in range(0, len(qids), 250):
        chunk = qids[i:i + 250]
        values = " ".join(f"wd:{q}" for q in chunk)
        query = f"""
        SELECT ?p (COUNT(DISTINCT ?t) AS ?nt) (COUNT(DISTINCT ?f) AS ?nf) WHERE {{
          VALUES ?p {{ {values} }}
          OPTIONAL {{ ?p wdt:P97 ?t }}
          OPTIONAL {{ ?p wdt:P53 ?f }}
        }} GROUP BY ?p"""
        r = requests.get(ENDPOINT, params={"query": query, "format": "json"},
                         headers=HEADERS, timeout=180)
        r.raise_for_status()
        for b in r.json()["results"]["bindings"]:
            q = b["p"]["value"].rsplit("/", 1)[-1]
            nt = int(b["nt"]["value"])
            nf = int(b["nf"]["value"])
            nobility[q] = {"title": nt > 0, "family": nf > 0, "noble": (nt > 0 or nf > 0)}
        time.sleep(0.5)
        print(f"  classified {min(i+250, len(qids))}/{len(qids)}", end="\r")

    with open(r"c:\NetworkScience\nobility.json", "w", encoding="utf-8") as fh:
        json.dump(nobility, fh, ensure_ascii=False, indent=1)

    nobles = sum(1 for v in nobility.values() if v["noble"])
    print(f"\nClassified {len(nobility)} nodes: {nobles} noble, {len(nobility)-nobles} commoner")


    cross = json.load(open(r"c:\NetworkScience\crosswalk.json", encoding="utf-8"))
    checks = {"Q10479": "Catherine (Kate)", "Q3304649": "Meghan", "Q924854": "Mark Phillips",
              "Q43274": "Charles III", "Q9682": "Elizabeth II", "Q36812": "William"}
    print("\nCalibration:")
    for q, name in checks.items():
        v = nobility.get(q)
        print(f"  {name:<18} {v if v else 'not in set'}")


if __name__ == "__main__":
    main()
