"""Zet een boek: van tekst.txt naar een drukklaar binnenwerk en omslag.

Gebruik: python3 gereedschap/bouw.py boeken/<titel> [--hulplijnen] [--voorbeeld]

Schrijft naar boeken/<titel>/uit/:
- binnenwerk.pdf  A6, aangevuld tot een veelvoud van vier pagina's;
- omslag.pdf      achterkant + rug + voorkant met 3 mm afloop;
met --hulplijnen ook omslag-hulplijnen.pdf (snijrand en rug zichtbaar),
met --voorbeeld PNG's van het omslag en de eerste pagina's om snel te bekijken.

Titel, auteur, kleur, achterflaptekst en jaar van de eerste druk komen uit het
boekbestand in site/boeken/ (via het nummer in boek.json); wat in boek.json staat gaat voor.
"""

import datetime
import json
import re
import sys
from pathlib import Path

import typst

WERKPLAATS = Path(__file__).resolve().parent.parent
SJABLONEN = WERKPLAATS / "sjablonen"
LETTERS = [str(SJABLONEN / "letters")]


def kleurcode(naam):
    """Zoekt de kleur (bijv. reeks-07) op in de stylesheet van de site en volgt var(--…)."""
    css = (WERKPLAATS / "site/statisch/uitvloed.css").read_text("utf-8")
    tokens = dict(re.findall(r"--([\w-]+):\s*([^;]+);", css))
    waarde = tokens.get(naam) or sys.exit(f"Kleur --{naam} staat niet in uitvloed.css.")
    while (m := re.fullmatch(r"var\(--([\w-]+)\)", waarde.strip())):
        waarde = tokens[m.group(1)]
    return waarde.strip()


def gegevens(map_):
    boek = json.loads((map_ / "boek.json").read_text("utf-8"))
    site = (json.loads(p.read_text("utf-8")) for p in sorted((WERKPLAATS / "site/boeken").glob("*.json")))
    uit_site = next((b for b in site if b["nummer"] == boek.get("nummer")), {})
    # Op de site is 'jaar' de eerste druk; in het colofon is het het jaar van deze uitgave.
    eerste_druk = uit_site.pop("jaar", None)
    samen = {**uit_site, **boek}
    samen.setdefault("achterflap", uit_site.get("tekst", []))
    if eerste_druk:
        samen.setdefault("oorspronkelijk", f"Eerste druk: {eerste_druk}.")
    samen.setdefault("jaar", datetime.date.today().year)
    for veld in ("titel", "auteur", "nummer", "kleur"):
        if veld not in samen:
            sys.exit(f"'{veld}' ontbreekt: zet het in {map_ / 'boek.json'} of in site/boeken/.")
    samen["kleurcode"] = kleurcode(samen["kleur"])
    return samen


def zet(sjabloon, uitvoer, invoer, formaat="pdf"):
    return typst.compile(str(SJABLONEN / sjabloon), output=str(uitvoer) if uitvoer else None,
                         root=str(WERKPLAATS), font_paths=LETTERS, ignore_system_fonts=True,
                         sys_inputs=invoer, format=formaat, ppi=110)


def main(argv):
    opties = {a for a in argv[1:] if a.startswith("--")}
    mappen = [a for a in argv[1:] if not a.startswith("--")]
    if len(mappen) != 1:
        sys.exit(__doc__)
    map_ = Path(mappen[0]).resolve()
    if not (map_ / "tekst.txt").exists():
        sys.exit(f"{map_ / 'tekst.txt'} bestaat niet: draai eerst gereedschap/opschonen.py.")
    uit = map_ / "uit"
    uit.mkdir(exist_ok=True)

    boek = gegevens(map_)
    invoer = {"boek": json.dumps(boek), "tekst": "/" + (map_ / "tekst.txt").relative_to(WERKPLAATS).as_posix()}

    zet("binnenwerk.typ", uit / "binnenwerk.pdf", invoer)
    paginas = json.loads(typst.query(str(SJABLONEN / "binnenwerk.typ"), "<paginas>", field="value", one=True,
                                     root=str(WERKPLAATS), font_paths=LETTERS, ignore_system_fonts=True,
                                     sys_inputs=invoer))

    # Rugdikte: aantal vellen (twee pagina's per vel) maal de dikte van het papier.
    rug = boek.get("rug_mm") or round(paginas / 2 * float(boek.get("papierdikte_mm", 0.1)), 1)
    boek["rug_mm"] = rug
    invoer["boek"] = json.dumps(boek)
    zet("omslag.typ", uit / "omslag.pdf", invoer)
    if "--hulplijnen" in opties:
        zet("omslag.typ", uit / "omslag-hulplijnen.pdf", {**invoer, "hulplijnen": "ja"})
    if "--voorbeeld" in opties:
        zet("omslag.typ", uit / "omslag.png", {**invoer, "hulplijnen": "ja"}, "png")
        for i, png in enumerate(zet("binnenwerk.typ", None, invoer, "png")[:8], 1):
            (uit / f"pagina-{i:02}.png").write_bytes(png)

    print(f"{boek['titel']} — {boek['auteur']} (uitvloed № {boek['nummer']:02})")
    print(f"  binnenwerk  {uit / 'binnenwerk.pdf'}: {paginas} pagina's, 105 × 148 mm")
    print(f"  omslag      {uit / 'omslag.pdf'}: rug {rug} mm, "
          f"vel {2 * 105 + rug + 6:.1f} × {148 + 6} mm (met 3 mm afloop)")


if __name__ == "__main__":
    main(sys.argv)
