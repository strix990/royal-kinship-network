# Royal Kinship Network

Pipeline that rebuilds the royal92 genealogy by fusing it with Wikidata, plus the
analysis scripts, the final dataset, the paper, and an interactive viewer.

## Install

```bash
pip install -r requirements.txt
```

Requires Python 3.9+ (`networkx`, `requests`, `matplotlib`, `scipy`).

## Run the pipeline

The scripts in `src/` run in this order. Each is standalone.

```bash
python src/gedcom_parser.py      # 1. parse the royal92 GEDCOM
python src/fetch_wikidata.py     # 2. harvest descendant closures of the 10 roots
python src/fetch_spouses.py      #    married-in spouses
python src/fetch_adoptions.py    #    adoption qualifiers (P1039)
python src/fetch_nobility.py     #    nobility (P97 / P53)
python src/fetch_extra_roots.py  #    Bonaparte extension layer
python src/match.py              # 3. entity resolution -> crosswalk.json
python src/merge.py              # 4. merge + blood-only cleaning
python src/check.py              #    data-quality audit
python src/analysis.py           # 5. structure, centrality, communities
python src/null_models.py        #    ER / BA null-model comparison
python src/hemophilia.py         #    hemophilia propagation
```

Figures and exports:

```bash
python src/pipeline_fig.py src/tree_fig.py src/hemophilia_fig.py src/endogamy_fig.py
python src/export_tree.py        # browser tree data
python src/export_gephi.py       # Gephi GEXF / GraphML
```

Stage 2 queries the live Wikidata SPARQL endpoint and takes several minutes. To
skip it and use the prebuilt result, start from the files already in `data/`.

**Paths:** each script has a base-path constant near the top
(`OUT = r"c:\NetworkScience"` or a `sys.path.insert`). Set it to your local
checkout before running.

## Open the viewer

Double-click `viewer/index.html` (self-contained, no server or internet needed).
Click a node to expand or collapse, type a name to search, scroll to zoom, drag to
pan.

## Layout

```
src/       pipeline scripts
data/      royal92.ged (input), royal_updated.ged/.json (output), crosswalk.json, nobility.json
figures/   paper figures
viewer/    self-contained interactive family tree
paper/     LaTeX source
```
