"""Schoont een ruwe brontekst op tot een tekst die het Typst-sjabloon kan zetten.

Gebruik: python3 gereedschap/opschonen.py boeken/<titel> [--opnieuw]

Leest `bron.txt` (en `boek.json` voor instellingen) en schrijft `tekst.txt`.
Daarna is `tekst.txt` de tekst waarin je corrigeert; het script overschrijft hem
alleen met --opnieuw, zodat je correcties niet verloren gaan.

Wat het doet:
- paginanummers en losse koppen/voetregels verdwijnen;
- woorden die aan het eind van een regel zijn afgebroken worden weer heel;
- regels binnen een alinea worden aan elkaar gezet;
- alinea's die door een paginawissel in tweeën zijn geknipt worden weer één;
- rechte aanhalingstekens worden gekrulde (' → ‘ ’, " → “ ”);
- hoofdstukkoppen krijgen een `# ` ervoor, scènewissels worden `***`.

Het resultaat bestaat uit alinea's gescheiden door één witregel.
"""

import json
import re
import sys
from collections import Counter
from pathlib import Path

# Een regel met alleen een paginanummer: "12", "- 12 -", "— 12 —", "[12]", "p. 12".
PAGINANUMMER = re.compile(r"^\s*(?:[-–—\[(]\s*)?(?:p\.\s*)?\d{1,4}(?:\s*[-–—\])])?\s*$")
# Een scènewissel: alleen sterretjes, streepjes of punten.
SCENEWISSEL = re.compile(r"^\s*(?:[*⁂]\s*){1,5}$|^\s*(?:[-–—.·]\s*){3,}$")
# Standaard hoofdstukkoppen: "HOOFDSTUK III", "Hoofdstuk 3", "III.", "3."
HOOFDSTUK_STANDAARD = r"^(?:HOOFDSTUK|Hoofdstuk)\s+[\wIVXLC]+\.?$|^[IVXLC]{1,7}\.?$|^\d{1,3}\.$"
# Tekens waarmee een alinea mag eindigen; eindigt ze anders, dan loopt ze waarschijnlijk door.
EINDTEKENS = ".!?…:;\"'»”’)]*"
AFBREEKSTREEPJE = re.compile(r"(\w)[-¬\u00ad]$")  # gewoon, ¬ of zacht afbreekstreepje
# Na deze tekens (of aan het begin) opent een aanhalingsteken; anders sluit het.
OPENT_NA = " \t\n([—–-"
# Weggevallen letters aan het begin van een woord: 't, 'k, 's, 'n, 'm, 'r, 'ns.
AFKAPPING = re.compile(r"'(?=(?:t|k|s|n|m|r|ns)\b)")


def lees_instellingen(map_):
    pad = map_ / "boek.json"
    return json.loads(pad.read_text("utf-8")) if pad.exists() else {}


def krul(tekst):
    """Vervangt rechte aanhalingstekens door gekrulde."""
    tekst = AFKAPPING.sub("’", tekst)
    uit = []
    for i, teken in enumerate(tekst):
        if teken in "'\"":
            opent = i == 0 or tekst[i - 1] in OPENT_NA
            teken = {"'": "‘’", '"': "“”"}[teken][0 if opent else 1]
        uit.append(teken)
    return "".join(uit)


def opschonen(ruw, instellingen=None):
    """Geeft (tekst, verslag) terug: de schone tekst en tellingen van wat er veranderde."""
    instellingen = instellingen or {}
    hoofdstuk = re.compile(instellingen.get("hoofdstukpatroon", HOOFDSTUK_STANDAARD))
    weg = [re.compile(p) for p in instellingen.get("weg", [])]
    verslag = Counter()
    heelgemaakt = []

    tekst = ruw.replace("\r\n", "\n").replace("\r", "\n").replace("\f", "\n\n").replace("﻿", "")
    regels = [r.rstrip() for r in tekst.split("\n")]

    # Kop- en voetregels die op bijna elke pagina terugkomen (de titel, de auteur) staan
    # vaak tussen een witregel en een paginanummer. Ze worden alleen weggehaald als ze
    # in `weg` staan; automatisch raden is te riskant voor een roman met refreinen.
    schoon = []
    for r in regels:
        if PAGINANUMMER.match(r):
            verslag["paginanummers"] += 1
            schoon.append("")
        elif any(p.search(r) for p in weg):
            verslag["kopregels"] += 1
            schoon.append("")
        else:
            schoon.append(r)

    # Regels groeperen tot blokken (gescheiden door één of meer witregels).
    blokken, huidig = [], []
    for r in schoon:
        if r.strip():
            huidig.append(r.strip())
        elif huidig:
            blokken.append(huidig)
            huidig = []
    if huidig:
        blokken.append(huidig)

    def plak(links, rechts):
        """Plakt twee stukken tekst; heelt een afgebroken woord op de naad."""
        if AFBREEKSTREEPJE.search(links):
            if rechts[:1].islower():
                woord = re.search(r"\w+$", links[:-1]).group() + re.match(r"\w*", rechts).group()
                heelgemaakt.append(woord)
                verslag["afbrekingen"] += 1
                return links[:-1] + rechts
            if links.endswith("-") and rechts[:1].isupper():
                return links + rechts  # samenstelling als Noord-Holland: streepje blijft
        return links + " " + rechts

    alineas = []  # lijst van (soort, tekst): soort is "kop", "wissel" of "tekst"
    for blok in blokken:
        if len(blok) == 1 and hoofdstuk.match(blok[0]):
            alineas.append(("kop", blok[0]))
            continue
        if len(blok) == 1 and SCENEWISSEL.match(blok[0]):
            alineas.append(("wissel", "***"))
            continue
        zin = blok[0]
        for r in blok[1:]:
            zin = plak(zin, r)
        zin = re.sub(r"[ \t]+", " ", zin)
        if instellingen.get("aanhalingstekens_krullen", True):
            zin = krul(zin)
        # Een alinea die midden in een zin stopt, loopt door na de paginawissel.
        vorige = alineas[-1] if alineas else None
        if (vorige and vorige[0] == "tekst" and zin[:1].islower()
                and not vorige[1].endswith(tuple(EINDTEKENS))):
            alineas[-1] = ("tekst", plak(vorige[1], zin))
            verslag["alineas samengevoegd"] += 1
        else:
            alineas.append(("tekst", zin))

    uit = []
    for soort, t in alineas:
        if soort == "kop":
            verslag["hoofdstukken"] += 1
            uit.append("# " + t)
        else:
            uit.append(t)
    verslag["alineas"] = sum(1 for s, _ in alineas if s == "tekst")
    return "\n\n".join(uit) + "\n", verslag, heelgemaakt


def main(argv):
    mappen = [a for a in argv[1:] if a != "--opnieuw"]
    if len(mappen) != 1:
        sys.exit("Gebruik: python3 gereedschap/opschonen.py boeken/<titel> [--opnieuw]")
    map_ = Path(mappen[0])
    bron = map_ / "bron.txt"
    if not bron.exists():
        sys.exit(f"{bron} bestaat niet: zet de ruwe tekst daar neer.")
    if (map_ / "tekst.txt").exists() and "--opnieuw" not in argv:
        sys.exit(f"{map_ / 'tekst.txt'} bestaat al en bevat misschien correcties. "
                 "Gebruik --opnieuw om hem te overschrijven.")
    tekst, verslag, heelgemaakt = opschonen(bron.read_text("utf-8"), lees_instellingen(map_))
    (map_ / "tekst.txt").write_text(tekst, "utf-8")
    print(f"{map_ / 'tekst.txt'} geschreven.")
    for sleutel in ("hoofdstukken", "alineas", "paginanummers", "kopregels", "afbrekingen", "alineas samengevoegd"):
        print(f"  {sleutel:22} {verslag[sleutel]}")
    if heelgemaakt:
        # Controleer deze lijst: "zee-en" hoort bijvoorbeeld niet "zeeen" te worden.
        (map_ / "afbrekingen.txt").write_text("\n".join(heelgemaakt) + "\n", "utf-8")
        print(f"  heelgemaakte woorden staan in {map_ / 'afbrekingen.txt'}")


if __name__ == "__main__":
    main(sys.argv)
