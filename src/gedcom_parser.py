import json
import re
from dataclasses import dataclass, field, asdict


@dataclass
class Individual:
    xref: str
    name: str = ""
    given: str = ""
    surname: str = ""
    sex: str = ""
    title: str = ""
    birth_date: str = ""
    birth_place: str = ""
    chr_date: str = ""
    death_date: str = ""
    death_place: str = ""
    buri_place: str = ""
    refn: str = ""
    fams: list = field(default_factory=list)
    famc: str = ""


@dataclass
class Family:
    xref: str
    husb: str = ""
    wife: str = ""
    chil: list = field(default_factory=list)
    marr_date: str = ""
    marr_place: str = ""
    divorced: bool = False


def _name_parts(name: str):
    m = re.match(r"^(.*?)/(.*?)/", name)
    if m:
        given = m.group(1).strip()
        surname = m.group(2).strip()
    else:
        given = name.strip()
        surname = ""
    return given, surname


def parse(path: str):
    individuals: dict[str, Individual] = {}
    families: dict[str, Family] = {}

    with open(path, "r", encoding="latin-1") as fh:
        lines = fh.readlines()

    cur = None
    cur_event = None

    for raw in lines:
        line = raw.rstrip("\n").rstrip("\r")
        if not line.strip():
            continue
        m = re.match(r"^(\d+)\s+(@\S+@|\S+)(?:\s+(.*))?$", line)
        if not m:
            continue
        level = int(m.group(1))
        tag = m.group(2)
        val = (m.group(3) or "").strip()

        if level == 0:
            cur_event = None
            if val == "INDI":
                xref = tag
                cur = Individual(xref=xref)
                individuals[xref] = cur
            elif val == "FAM":
                xref = tag
                cur = Family(xref=xref)
                families[xref] = cur
            else:
                cur = None
            continue

        if cur is None:
            continue

        if isinstance(cur, Individual):
            if level == 1:
                cur_event = None
                if tag == "NAME":
                    cur.name = val
                    cur.given, cur.surname = _name_parts(val)
                elif tag == "SEX":
                    cur.sex = val
                elif tag == "TITL":
                    cur.title = val
                elif tag == "REFN":
                    cur.refn = val
                elif tag == "FAMS":
                    cur.fams.append(val)
                elif tag == "FAMC":
                    cur.famc = val
                elif tag in ("BIRT", "DEAT", "BURI", "CHR"):
                    cur_event = tag
            elif level == 2 and cur_event:
                if tag == "DATE":
                    if cur_event == "BIRT":
                        cur.birth_date = val
                    elif cur_event == "CHR":
                        cur.chr_date = val
                    elif cur_event == "DEAT":
                        cur.death_date = val
                elif tag == "PLAC":
                    if cur_event == "BIRT":
                        cur.birth_place = val
                    elif cur_event == "DEAT":
                        cur.death_place = val
                    elif cur_event == "BURI":
                        cur.buri_place = val

        elif isinstance(cur, Family):
            if level == 1:
                cur_event = None
                if tag == "HUSB":
                    cur.husb = val
                elif tag == "WIFE":
                    cur.wife = val
                elif tag == "CHIL":
                    cur.chil.append(val)
                elif tag == "DIV":
                    cur.divorced = True
                elif tag == "MARR":
                    cur_event = "MARR"
            elif level == 2 and cur_event == "MARR":
                if tag == "DATE":
                    cur.marr_date = val
                elif tag == "PLAC":
                    cur.marr_place = val

    return individuals, families


def extract_year(date_str: str):
    m = re.search(r"(\d{4})", date_str or "")
    return int(m.group(1)) if m else None


if __name__ == "__main__":
    indi, fam = parse(r"c:\NetworkScience\royal92.ged")
    print(f"Individuals parsed: {len(indi)}")
    print(f"Families parsed:    {len(fam)}")


    with_birth = sum(1 for i in indi.values() if i.birth_date)
    with_death = sum(1 for i in indi.values() if i.death_date)
    living_1992 = sum(1 for i in indi.values() if not i.death_date and extract_year(i.birth_date) and extract_year(i.birth_date) > 1900)
    print(f"  with birth date: {with_birth}")
    print(f"  with death date: {with_death}")
    print(f"  no death + born >1900 (update candidates): {living_1992}")


    v = indi["@I1@"]
    print(f"\nSpot check @I1@: {v.given} {v.surname} | {v.title} | b.{v.birth_date} d.{v.death_date}")


    out = {
        "individuals": {k: asdict(v) for k, v in indi.items()},
        "families": {k: asdict(v) for k, v in fam.items()},
    }
    with open(r"c:\NetworkScience\royal92_parsed.json", "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print("\nWrote royal92_parsed.json")
