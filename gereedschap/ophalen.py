"""Haalt de brontekst van een boek op bij Project Gutenberg.

Gebruik: python3 gereedschap/ophalen.py boeken/<titel> [--opnieuw]

Leest het e-booknummer uit `gutenberg` in boek.json, downloadt de platte tekst
(UTF-8), knipt de Gutenberg-kop en -licentie eraf en schrijft:
- bron.txt       de tekst tussen *** START … *** en *** END … ***;
- herkomst.json  waar en wanneer de tekst vandaan kwam, met titel en auteur volgens Gutenberg.

Het script stopt als de auteur volgens Gutenberg niet overeenkomt met boek.json,
zodat een verkeerd nummer niet ongemerkt een ander boek oplevert.
Een bestaande bron.txt wordt alleen met --opnieuw overschreven.

De naam Project Gutenberg hoort niet in het gedrukte boek: wie de licentie weghaalt,
mag hun merknaam niet gebruiken. De herkomst staat daarom alleen in herkomst.json.
"""

import datetime
import json
import re
import sys
import time
import unicodedata
import urllib.request
from pathlib import Path

ADRES = "https://www.gutenberg.org/cache/epub/{nr}/pg{nr}.txt"
START = re.compile(r"^\*\*\* ?START OF (?:THE|THIS) PROJECT GUTENBERG EBOOK.*\*\*\*\s*$", re.M)
EINDE = re.compile(r"^\*\*\* ?END OF (?:THE|THIS) PROJECT GUTENBERG EBOOK.*\*\*\*\s*$", re.M)


def uit_gutenberg(ruw):
    """Geeft (kop, tekst): de velden uit de Gutenberg-kop en de tekst zonder kop en licentie."""
    ruw = ruw.replace("\r\n", "\n").lstrip("﻿")
    start, einde = START.search(ruw), EINDE.search(ruw)
    if not start or not einde:
        raise ValueError("geen *** START/END OF THE PROJECT GUTENBERG EBOOK *** gevonden")
    kop = {}
    # Velden als "Title: …", met vervolgregels die inspringen (lange titels).
    for m in re.finditer(r"^(\w[\w ]*): (.*(?:\n[ \t]+\S.*)*)", ruw[:start.start()], re.M):
        kop[m.group(1).lower()] = re.sub(r"\s+", " ", m.group(2)).strip()
    tekst = ruw[start.end():einde.start()].strip("\n")
    # Soms staat de naam van de maker nog bovenaan: "Produced by … Distributed Proofreading …".
    tekst = re.sub(r"\A(?:Produced by|This e-?book was produced by).*?(?:\n\s*\n|\Z)", "", tekst, flags=re.S | re.I)
    # En onderaan soms nog "End of Project Gutenberg's …".
    tekst = re.sub(r"\n\s*End of (?:the )?Project Gutenberg.*\Z", "", tekst, flags=re.S | re.I)
    return kop, tekst.strip("\n") + "\n"


def letters(tekst):
    """Kleine letters zonder accenten, voor het vergelijken van namen."""
    return unicodedata.normalize("NFKD", tekst).encode("ascii", "ignore").decode().lower()


def zelfde_auteur(volgens_boek, volgens_gutenberg):
    """Komt de achternaam uit boek.json voor in de auteur volgens Gutenberg?"""
    achternaam = letters(volgens_boek).split()[-1]
    return achternaam in re.findall(r"\w+", letters(volgens_gutenberg))


def download(adres, pogingen=4):
    for poging in range(pogingen):
        try:
            verzoek = urllib.request.Request(adres, headers={"User-Agent": "uitvloed-werkplaats"})
            with urllib.request.urlopen(verzoek, timeout=60) as antwoord:
                return antwoord.read().decode("utf-8")
        except OSError as fout:
            if poging == pogingen - 1:
                raise
            print(f"  {fout}; opnieuw over {2 ** (poging + 1)} s")
            time.sleep(2 ** (poging + 1))


def main(argv):
    mappen = [a for a in argv[1:] if a != "--opnieuw"]
    if len(mappen) != 1:
        sys.exit(__doc__)
    map_ = Path(mappen[0])
    boek = json.loads((map_ / "boek.json").read_text("utf-8"))
    if "gutenberg" not in boek:
        sys.exit(f"Zet het e-booknummer als 'gutenberg' in {map_ / 'boek.json'}.")
    if (map_ / "bron.txt").exists() and "--opnieuw" not in argv:
        sys.exit(f"{map_ / 'bron.txt'} bestaat al. Gebruik --opnieuw om hem te vervangen.")

    adres = ADRES.format(nr=boek["gutenberg"])
    print(f"Ophalen: {adres}")
    kop, tekst = uit_gutenberg(download(adres))
    if "auteur" in boek and not zelfde_auteur(boek["auteur"], kop.get("author", "")):
        sys.exit(f"Gutenberg #{boek['gutenberg']} is van {kop.get('author', 'onbekend')!r}, "
                 f"niet van {boek['auteur']!r}. Klopt het nummer?")

    (map_ / "bron.txt").write_text(tekst, "utf-8")
    herkomst = {"bron": adres, "gutenberg": boek["gutenberg"], "opgehaald": datetime.date.today().isoformat(),
                **{k: kop[k] for k in ("title", "author", "language", "release date", "credits") if k in kop}}
    (map_ / "herkomst.json").write_text(json.dumps(herkomst, ensure_ascii=False, indent=2) + "\n", "utf-8")
    print(f"  {kop.get('title')} — {kop.get('author')}: {len(tekst.splitlines())} regels in {map_ / 'bron.txt'}")


if __name__ == "__main__":
    main(sys.argv)
