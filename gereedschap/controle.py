"""Controleert een gezet boek voordat het naar de drukker gaat.

Gebruik: python3 gereedschap/controle.py boeken/<titel>

Draai eerst gereedschap/bouw.py. Het script kijkt naar:
- rechten:     is de auteur langer dan 70 jaar dood (`sterfjaar` in boek.json),
               of staat er in `rechtenvrij` waarom het boek gedrukt mag worden;
- binnenwerk:  elke pagina 105 × 148 mm, paginatal een veelvoud van vier;
- omslag:      één pagina, zo groot als achterkant + rug + voorkant met 3 mm afloop,
               en de rug past bij het paginatal van het binnenwerk;
- lettertypes: alle lettertypes in beide PDF's ingebed;
- tekst.txt:   wat het opschonen kan hebben laten staan (paginanummers, rechte
               aanhalingstekens, zachte afbreekstreepjes) en alinea's met een
               oneven aantal _ (cursief dat niet sluit).

Fouten (✗) houden het boek tegen; waarschuwingen (!) zijn om na te kijken.
Komt er een fout uit, dan eindigt het script met code 1.
Een geslaagde controle vervangt de proefdruk niet.
"""

import datetime
import re
import sys
from pathlib import Path

from pypdf import PdfReader

from bouw import gegevens, rugdikte

MM = 72 / 25.4  # PDF-punten per millimeter
BREEDTE, HOOGTE, AFLOOP = 105, 148, 3  # zoals in sjablonen/uitvloed.typ
VEELVOUD = 4  # binnenwerk.typ vult aan tot een veelvoud van vier
SPELING = 0.3  # mm


def fout(melding):
    return ("✗", melding)


def waarschuwing(melding):
    return ("!", melding)


def goed(melding):
    return ("✓", melding)


def rechten(boek, jaar=None):
    """Auteursrecht loopt tot 1 januari van het 71e jaar na de dood (Auteurswet, art. 37–38).

    `sterfjaar` mag een lijst zijn (auteur, vertaler, illustrator): het laatste jaar telt.
    """
    jaar = jaar or datetime.date.today().year
    if boek.get("rechtenvrij"):
        return [goed(f"rechten: {boek['rechtenvrij']}")]
    sterfjaar = boek.get("sterfjaar")
    if sterfjaar is None:
        return [fout("rechten: zet 'sterfjaar' (of 'rechtenvrij' met een reden) in boek.json")]
    laatste = max(sterfjaar) if isinstance(sterfjaar, list) else sterfjaar
    vrij = laatste + 71
    if jaar < vrij:
        return [fout(f"rechten: overleden in {laatste}, rechtenvrij pas op 1 januari {vrij}")]
    return [goed(f"rechten: overleden in {laatste}, rechtenvrij sinds 1 januari {vrij}")]


def maat(pagina):
    """Breedte en hoogte van een pagina in mm."""
    vak = pagina.mediabox
    return float(vak.width) / MM, float(vak.height) / MM


def klopt(gemeten, verwacht):
    return abs(gemeten - verwacht) <= SPELING


def binnenwerk(pdf):
    meldingen = []
    afwijkend = [i for i, p in enumerate(pdf.pages, 1)
                 if not all(map(klopt, maat(p), (BREEDTE, HOOGTE)))]
    if afwijkend:
        b, h = maat(pdf.pages[afwijkend[0] - 1])
        meldingen.append(fout(f"binnenwerk: {len(afwijkend)} pagina('s) niet {BREEDTE} × {HOOGTE} mm, "
                              f"te beginnen bij pagina {afwijkend[0]} ({b:.1f} × {h:.1f} mm)"))
    else:
        meldingen.append(goed(f"binnenwerk: alle pagina's {BREEDTE} × {HOOGTE} mm"))
    paginas = len(pdf.pages)
    if paginas % VEELVOUD:
        meldingen.append(fout(f"binnenwerk: {paginas} pagina's, geen veelvoud van {VEELVOUD}"))
    else:
        meldingen.append(goed(f"binnenwerk: {paginas} pagina's"))
    return meldingen


def omslag(pdf, rug):
    if len(pdf.pages) != 1:
        return [fout(f"omslag: {len(pdf.pages)} pagina's, verwacht één vel")]
    verwacht = (2 * BREEDTE + rug + 2 * AFLOOP, HOOGTE + 2 * AFLOOP)
    gemeten = maat(pdf.pages[0])
    tekst = f"{gemeten[0]:.1f} × {gemeten[1]:.1f} mm"
    if not all(map(klopt, gemeten, verwacht)):
        return [fout(f"omslag: {tekst}, verwacht {verwacht[0]:.1f} × {verwacht[1]:.1f} mm "
                     f"bij een rug van {rug} mm; zet het boek opnieuw met bouw.py")]
    meldingen = [goed(f"omslag: {tekst}, rug {rug} mm")]
    if rug < 5:
        meldingen.append(waarschuwing(f"omslag: rug {rug} mm is te smal voor rugtekst en blijft leeg"))
    return meldingen


def lettertypes(pdf):
    """Namen van lettertypes zonder ingebed letterbestand, ook in formulieren (XObjects)."""
    missend, gezien = set(), set()

    def bekijk(bronnen):
        if not bronnen or id(bronnen) in gezien:
            return
        gezien.add(id(bronnen))
        for letter in (bronnen.get("/Font") or {}).values():
            letter = letter.get_object()
            if letter.get("/Subtype") == "/Type3":
                continue  # Type 3 bestaat uit tekenopdrachten in de PDF zelf
            if letter.get("/Subtype") == "/Type0":
                letter = letter["/DescendantFonts"][0].get_object()
            beschrijving = (letter.get("/FontDescriptor") or {})
            if not any(k in beschrijving for k in ("/FontFile", "/FontFile2", "/FontFile3")):
                missend.add(str(letter.get("/BaseFont", "?")).lstrip("/"))
        for object_ in (bronnen.get("/XObject") or {}).values():
            object_ = object_.get_object()
            if object_.get("/Subtype") == "/Form":
                bekijk(object_.get("/Resources"))

    for pagina in pdf.pages:
        bekijk(pagina.get("/Resources"))
    return missend


def tekst(inhoud):
    """Resten die het opschonen kan hebben laten staan; alleen waarschuwingen."""
    alineas = inhoud.split("\n\n")
    meldingen = []
    nummers = [a for a in alineas if re.fullmatch(r"\s*\d{1,4}\s*", a)]
    if nummers:
        meldingen.append(waarschuwing(f"tekst.txt: {len(nummers)} alinea('s) met alleen een getal "
                                      f"(paginanummer?), bijv. {nummers[0].strip()}"))
    open_cursief = [a for a in alineas if a.count("_") % 2]
    if open_cursief:
        meldingen.append(waarschuwing(f"tekst.txt: {len(open_cursief)} alinea('s) met cursief dat niet sluit "
                                      f"(oneven aantal _), bijv. „{open_cursief[0][:60]}”"))
    for teken, naam in (("'", "rechte enkele aanhalingstekens"), ('"', "rechte dubbele aanhalingstekens"),
                        ("­", "zachte afbreekstreepjes"), ("¬", "afbreektekens ¬")):
        if (aantal := inhoud.count(teken)):
            meldingen.append(waarschuwing(f"tekst.txt: {aantal} {naam}"))
    return meldingen


def controleer(map_):
    boek = gegevens(map_)
    meldingen = rechten(boek)
    uit = map_ / "uit"
    pdfs = {naam: uit / f"{naam}.pdf" for naam in ("binnenwerk", "omslag")}
    for naam, pad in pdfs.items():
        if not pad.exists():
            return meldingen + [fout(f"{naam}: {pad} bestaat niet; draai eerst gereedschap/bouw.py")]
    binnen, kaft = (PdfReader(p) for p in pdfs.values())
    meldingen += binnenwerk(binnen)
    meldingen += omslag(kaft, rugdikte(boek, len(binnen.pages)))
    for naam, pdf in (("binnenwerk", binnen), ("omslag", kaft)):
        if (missend := lettertypes(pdf)):
            meldingen.append(fout(f"{naam}: niet ingebed: {', '.join(sorted(missend))}"))
        else:
            meldingen.append(goed(f"{naam}: alle lettertypes ingebed"))
    meldingen += tekst((map_ / "tekst.txt").read_text("utf-8"))
    return meldingen


def main(argv):
    if len(argv) != 2:
        sys.exit(__doc__)
    map_ = Path(argv[1]).resolve()
    meldingen = controleer(map_)
    for teken, melding in meldingen:
        print(f"{teken} {melding}")
    fouten = sum(teken == "✗" for teken, _ in meldingen)
    print(f"\n{fouten} fout(en). " + ("Niet naar de drukker." if fouten else "Klaar voor een proefdruk."))
    sys.exit(1 if fouten else 0)


if __name__ == "__main__":
    main(sys.argv)
