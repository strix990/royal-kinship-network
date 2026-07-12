import json
import time
import requests

ENDPOINT = "https://query.wikidata.org/sparql"
HEADERS = {"User-Agent": "RoyalNetworkProject/1.0 (academic course project)"}


def qid(uri):
    return uri.rsplit("/", 1)[-1] if uri else ""


def fetch_batch(qids):
    values = " ".join(f"wd:{q}" for q in qids)
    query = f"""
    SELECT ?p ?pLabel ?birth ?death ?gender WHERE {{
      VALUES ?p {{ {values} }}
      OPTIONAL {{ ?p wdt:P569 ?birth }}
      OPTIONAL {{ ?p wdt:P570 ?death }}
      OPTIONAL {{ ?p wdt:P21 ?gender }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
    }}"""
    r = requests.get(ENDPOINT, params={"query": query, "format": "json"},
                     headers=HEADERS, timeout=120)
    r.raise_for_status()
    return r.json()["results"]["bindings"]


def main():
    with open(r"c:\NetworkScience\wikidata_people.json", encoding="utf-8") as fh:
        people = json.load(fh)

    referenced = set()
    for rec in people.values():
        referenced.update(rec["fathers"])
        referenced.update(rec["mothers"])
        referenced.update(rec["spouses"])
    missing = sorted(referenced - set(people.keys()))
    print(f"Referenced-but-unfetched people (spouses/parents): {len(missing)}")

    added = 0
    for i in range(0, len(missing), 200):
        chunk = missing[i:i + 200]
        for b in fetch_batch(chunk):
            pq = qid(b["p"]["value"])
            if pq in people:
                continue
            people[pq] = {
                "qid": pq,
                "label": b.get("pLabel", {}).get("value", ""),
                "birth": b.get("birth", {}).get("value", "")[:10],
                "death": b.get("death", {}).get("value", "")[:10],
                "gender": qid(b.get("gender", {}).get("value", "")),
                "fathers": [], "mothers": [], "spouses": [],
            }
            added += 1
        time.sleep(1)

    with open(r"c:\NetworkScience\wikidata_people.json", "w", encoding="utf-8") as fh:
        json.dump(people, fh, ensure_ascii=False, indent=1)
    print(f"Added {added} married-in / external nodes. Total now: {len(people)}")


if __name__ == "__main__":
    main()
