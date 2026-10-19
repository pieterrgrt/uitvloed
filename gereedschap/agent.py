"""Laat Claude een boek klaarmaken: van Gutenberg-tekst tot een boek dat door de controle komt.

Gebruik: python3 gereedschap/agent.py boeken/<titel> [--stappen 80] [--model claude-opus-5-5]

Wat vastligt doen de scripts (ophalen, opschonen, bouw, controle); de agent doet het
oordeelswerk ertussen: het hoofdstukpatroon vinden, de titelpagina van de bron weghalen,
heelgemaakte afbrekingen en cursief nakijken, kennelijke tikfouten verbeteren en een
concept-achterflap schrijven. Hij werkt alleen in boeken/<titel>/ en raakt de rechten
(`sterfjaar`, `rechtenvrij`), het ISBN en het nummer niet aan.

Ontbreekt bron.txt, dan haalt het script hem eerst op (`gutenberg` in boek.json);
ontbreekt tekst.txt, dan schoont het hem eerst op. Wat de agent deed en wat jij nog moet
nakijken staat daarna in werkverslag.md. Bekijk zijn wijzigingen met
`git diff boeken/<titel>` en lees de PDF voordat er iets naar de drukker gaat.

Nodig: ANTHROPIC_API_KEY (of een `ant auth login`-profiel) en `pip install -r gereedschap/requirements.txt`.
"""

import argparse
import datetime
import json
import re
import subprocess
import sys
from pathlib import Path

import anthropic
from anthropic import beta_tool

from controle import tekst as tekstcontrole

GEREEDSCHAP = Path(__file__).resolve().parent
MODEL = "claude-opus-5-5"
LEESBAAR = ("bron.txt", "tekst.txt", "afbrekingen.txt", "boek.json", "werkverslag.md", "herkomst.json")
# Velden in boek.json die de agent mag zetten. Rechten, ISBN, nummer, titel en auteur blijven van jou.
INSTELBAAR = {"hoofdstukpatroon", "onderkoppatroon", "weg", "aanhalingstekens_krullen", "streepjes", "achterflap"}
MAX_REGELS = 300

OPDRACHT = """\
Je maakt een boek klaar voor uitvloed, een kleine uitgeverij die Nederlandse literatuur
opnieuw drukt als A6-pocket. De brontekst komt meestal van Project Gutenberg. Scripts doen
het vaste werk; jij doet het oordeelswerk en gebruikt daarvoor de gereedschappen.

Hoe tekst.txt eruitziet (het sjabloon zet dit om):
- alinea's gescheiden door één witregel, elke alinea op één regel;
- `# Kop` is een hoofdstuk (nieuwe pagina), `## Kop` een onderdeel binnen een hoofdstuk;
- `***` is een scènewissel;
- `> tekst` is een motto, opdracht of citaat (ingesprongen, kleiner);
- `_cursief_` binnen één alinea; `[12]` is een verwijzing naar een noot.

Werkwijze:
1. Bekijk met `overzicht` en `lees` hoe de bron in elkaar zit: titelpagina, opdracht,
   motto's, hoofdstukkoppen, onderkoppen, kopregels, noten.
2. Zet zo nodig `hoofdstukpatroon`, `onderkoppatroon` en `weg` met `instellen` en draai
   `opschonen` tot de hoofdstukken kloppen. Opschonen overschrijft tekst.txt: doe dit
   vóórdat je met de hand gaat verbeteren.
3. Verbeter daarna in tekst.txt met `vervang`:
   - haal de titelpagina van de bron weg (titel, ondertitel, „door”, auteursnaam): het
     sjabloon maakt een eigen titelpagina en colofon;
   - opdracht en motto's horen bij het werk: laat ze staan en maak er `> `-alinea's van;
   - kijk afbrekingen.txt na: woorden die aan elkaar zijn gezet maar een streepje
     horen te houden, of andersom;
   - herstel cursief dat niet sluit en kennelijke fouten uit de digitalisering.
4. Schrijf met `instellen` een concept voor `achterflap`: twee of drie korte alinea's
   (samen hooguit 110 woorden) die zeggen waar het boek over gaat en waarom het nog
   gelezen wordt. Zakelijk en warm, geen superlatieven, geen ontknoping verklappen.
5. Draai `bouwen` (zet het boek en controleert het) tot er geen fouten (✗) meer zijn,
   en kijk de waarschuwingen (!) na.
6. Schrijf met `verslag` wat je veranderde en wat een mens nog moet beslissen.

Regels:
- Spelling en interpunctie van de auteur blijven zoals ze zijn. Moderniseer niets:
  „zyn”, „menschen”, „koffi” en „elkaâr” zijn geen fouten. Verbeter alleen wat
  aantoonbaar een fout van de digitalisering is, en noem elke inhoudelijke twijfel in
  het verslag in plaats van te gokken.
- Je verandert nooit de tekst van het werk zelf: geen zinnen weg, geen zinnen erbij.
- Noten blijven waar ze staan; zeg in het verslag hoe ze erbij staan als dat aandacht vraagt.
- Werk met kleine stukken tegelijk (`lees` met een bereik, `zoek` met een patroon);
  lees niet het hele boek door.
"""


class Werkbank:
    """De handelingen van de agent op één boekmap, los van de API zodat ze te testen zijn."""

    def __init__(self, map_):
        self.map = Path(map_).resolve()
        self.handwerk = False  # zijn er sinds het laatste opschonen wijzigingen in tekst.txt?
        self.kop = None  # komt boven het eerste stuk dat de agent in werkverslag.md zet

    def pad(self, bestand):
        if bestand not in LEESBAAR:
            raise ValueError(f"onbekend bestand {bestand!r}; kies uit {', '.join(LEESBAAR)}")
        return self.map / bestand

    def draai(self, script, *argumenten):
        uit = subprocess.run([sys.executable, str(GEREEDSCHAP / script), str(self.map), *argumenten],
                             capture_output=True, text=True, cwd=GEREEDSCHAP.parent)
        return (uit.stdout + uit.stderr).strip() + f"\n(exitcode {uit.returncode})"

    def overzicht(self):
        tekst = (self.map / "tekst.txt").read_text("utf-8")
        regels = tekst.split("\n")
        koppen = [f"{i}: {r}" for i, r in enumerate(regels, 1) if r.startswith("#")]
        hoofdletters = [f"{i}: {r}" for i, r in enumerate(regels, 1)
                        if r and not r.startswith("#") and len(r) < 60 and r.upper() == r and re.search(r"[A-Z]", r)]
        delen = [f"tekst.txt: {sum(1 for r in regels if r.strip())} alinea's, {len(regels)} regels",
                 f"koppen ({len(koppen)}):", *koppen[:120]]
        if len(koppen) > 120:
            delen.append(f"… en nog {len(koppen) - 120}")
        delen += [f"korte alinea's in hoofdletters ({len(hoofdletters)}), vaak resten van een titelpagina:",
                  *hoofdletters[:30]]
        delen += ["controle van de tekst:", *(f"{t} {m}" for t, m in tekstcontrole(tekst))]
        if (self.map / "afbrekingen.txt").exists():
            aantal = len((self.map / "afbrekingen.txt").read_text("utf-8").split())
            delen.append(f"afbrekingen.txt: {aantal} heelgemaakte woorden")
        return "\n".join(delen)

    def lees(self, bestand, vanaf=1, aantal=100):
        regels = self.pad(bestand).read_text("utf-8").split("\n")
        vanaf, aantal = max(1, vanaf), min(max(1, aantal), MAX_REGELS)
        stuk = regels[vanaf - 1:vanaf - 1 + aantal]
        kop = f"{bestand}, regels {vanaf}–{vanaf + len(stuk) - 1} van {len(regels)}"
        return kop + "\n" + "\n".join(f"{i}\t{r}" for i, r in enumerate(stuk, vanaf))

    def zoek(self, patroon, bestand="tekst.txt", hoogstens=40):
        regex = re.compile(patroon)
        regels = self.pad(bestand).read_text("utf-8").split("\n")
        treffers = [(i, r) for i, r in enumerate(regels, 1) if regex.search(r)]
        uit = [f"{len(treffers)} treffers voor /{patroon}/ in {bestand}"]
        for i, r in treffers[:hoogstens]:
            m = regex.search(r)
            begin = max(0, m.start() - 80)
            uit.append(f"{i}\t{'…' if begin else ''}{r[begin:m.end() + 80]}{'…' if m.end() + 80 < len(r) else ''}")
        return "\n".join(uit)

    def vervang(self, oud, nieuw, alle=False):
        pad = self.map / "tekst.txt"
        tekst = pad.read_text("utf-8")
        aantal = tekst.count(oud)
        if aantal == 0:
            raise ValueError("de oude tekst staat niet in tekst.txt; kopieer hem precies (met `lees`)")
        if aantal > 1 and not alle:
            raise ValueError(f"de oude tekst staat {aantal} keer in tekst.txt; neem meer context of zet alle=true")
        pad.write_text(tekst.replace(oud, nieuw), "utf-8")
        self.handwerk = True
        return f"{aantal} keer vervangen"

    def instellen(self, veld, waarde):
        if veld not in INSTELBAAR:
            raise ValueError(f"{veld!r} mag je niet zetten; wel: {', '.join(sorted(INSTELBAAR))}")
        if veld in ("hoofdstukpatroon", "onderkoppatroon"):
            re.compile(waarde)
        if veld == "weg":
            if not (isinstance(waarde, list) and all(isinstance(p, str) for p in waarde)):
                raise ValueError("'weg' is een lijst reguliere expressies")
            for p in waarde:
                re.compile(p)
        if veld == "achterflap" and not (isinstance(waarde, list) and all(isinstance(a, str) for a in waarde)):
            raise ValueError("'achterflap' is een lijst alinea's")
        pad = self.map / "boek.json"
        boek = json.loads(pad.read_text("utf-8"))
        boek[veld] = waarde
        pad.write_text(json.dumps(boek, ensure_ascii=False, indent=2) + "\n", "utf-8")
        return f"{veld} gezet"

    def opschonen(self, toch=False):
        if self.handwerk and not toch:
            raise ValueError("tekst.txt heeft verbeteringen die opschonen zou overschrijven; zet toch=true als dat de bedoeling is")
        self.handwerk = False
        return self.draai("opschonen.py", "--opnieuw")

    def bouwen(self):
        bouw = self.draai("bouw.py")
        if not bouw.endswith("(exitcode 0)"):
            return "bouwen mislukt:\n" + bouw
        return bouw + "\n\n" + self.draai("controle.py")

    def verslag(self, tekst):
        with (self.map / "werkverslag.md").open("a", encoding="utf-8") as f:
            if self.kop:
                f.write(self.kop.rstrip() + "\n\n")
                self.kop = None
            f.write(tekst.rstrip() + "\n\n")
        return "toegevoegd aan werkverslag.md"


def gereedschappen(bank):
    """De handelingen van de Werkbank als tools voor Claude. Fouten gaan als foutmelding terug."""

    def veilig(functie, *argumenten, **opties):
        try:
            return functie(*argumenten, **opties)
        except (ValueError, re.error, OSError) as fout:
            return f"Fout: {fout}"

    @beta_tool
    def overzicht() -> str:
        """Overzicht van tekst.txt: aantal alinea's, alle koppen met regelnummer, korte alinea's
        in hoofdletters (vaak resten van een titelpagina) en wat de tekstcontrole opmerkt."""
        return veilig(bank.overzicht)

    @beta_tool
    def lees(bestand: str, vanaf: int = 1, aantal: int = 100) -> str:
        """Leest regels uit een bestand in de boekmap, met regelnummers. Hoogstens 300 regels per keer.

        Args:
            bestand: bron.txt, tekst.txt, afbrekingen.txt, boek.json, werkverslag.md of herkomst.json.
            vanaf: eerste regel (vanaf 1).
            aantal: aantal regels.
        """
        return veilig(bank.lees, bestand, vanaf, aantal)

    @beta_tool
    def zoek(patroon: str, bestand: str = "tekst.txt") -> str:
        """Zoekt met een reguliere expressie (Python) en geeft hoogstens 40 treffers met regelnummer en context.

        Args:
            patroon: reguliere expressie, bijv. "^# " of "\\bmyn\\b".
            bestand: waarin te zoeken; standaard tekst.txt.
        """
        return veilig(bank.zoek, patroon, bestand)

    @beta_tool
    def vervang(oud: str, nieuw: str, alle: bool = False) -> str:
        """Vervangt een stuk tekst in tekst.txt. De oude tekst moet er precies één keer in staan,
        tenzij alle=true. Om een alinea weg te halen: neem de witregel erna mee in `oud`.

        Args:
            oud: de tekst zoals hij er nu staat, letterlijk.
            nieuw: de nieuwe tekst (leeg om weg te halen).
            alle: alle voorkomens vervangen.
        """
        return veilig(bank.vervang, oud, nieuw, alle)

    @beta_tool
    def instellen(veld: str, waarde_json: str) -> str:
        """Zet een veld in boek.json. Toegestaan: hoofdstukpatroon, onderkoppatroon (reguliere
        expressies voor een kopregel die alleen in een blok staat), weg (lijst reguliere expressies
        voor regels die weg moeten, bijv. kopregels), aanhalingstekens_krullen en streepjes
        (true/false) en achterflap (lijst alinea's).

        Args:
            veld: naam van het veld.
            waarde_json: de waarde als JSON, bijv. "\\"^[IVXLC]+\\\\.$\\"" of "[\\"alinea 1\\", \\"alinea 2\\"]".
        """
        try:
            waarde = json.loads(waarde_json)
        except json.JSONDecodeError as fout:
            return f"Fout: geen geldige JSON ({fout})"
        return veilig(bank.instellen, veld, waarde)

    @beta_tool
    def opschonen(toch: bool = False) -> str:
        """Schoont bron.txt opnieuw op met de instellingen uit boek.json en overschrijft tekst.txt
        en afbrekingen.txt. Weigert als je tekst.txt al met de hand verbeterde, tenzij toch=true.

        Args:
            toch: ook opschonen als dat verbeteringen in tekst.txt overschrijft.
        """
        return veilig(bank.opschonen, toch)

    @beta_tool
    def bouwen() -> str:
        """Zet het boek (binnenwerk en omslag) en draait de controle. Geeft het verslag van beide;
        ✗ is een fout die weg moet, ! een waarschuwing om na te kijken."""
        return veilig(bank.bouwen)

    @beta_tool
    def verslag(tekst: str) -> str:
        """Voegt Markdown toe aan werkverslag.md: wat je veranderde en wat een mens nog moet beslissen.

        Args:
            tekst: de toe te voegen tekst.
        """
        return veilig(bank.verslag, tekst)

    return [overzicht, lees, zoek, vervang, instellen, opschonen, bouwen, verslag]


def voorbereiden(map_):
    """Haalt de bron op en schoont hem op als dat nog niet gebeurd is (zonder de agent)."""
    for bestand, script in (("bron.txt", "ophalen.py"), ("tekst.txt", "opschonen.py")):
        if not (map_ / bestand).exists():
            subprocess.run([sys.executable, str(GEREEDSCHAP / script), str(map_)], check=True)


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("map", help="boeken/<titel>")
    parser.add_argument("--stappen", type=int, default=80, help="hoogstens zoveel rondes met de API")
    parser.add_argument("--model", default=MODEL)
    opties = parser.parse_args(argv[1:])
    map_ = Path(opties.map).resolve()
    voorbereiden(map_)
    client = anthropic.Anthropic()
    bank = Werkbank(map_)
    boek = json.loads((map_ / "boek.json").read_text("utf-8"))
    bank.kop = (f"## Werkverslag {datetime.date.today().isoformat()}\n\n"
                 f"Agent aan het werk op {boek.get('titel', map_.name)} — {boek.get('auteur', '?')}.")

    runner = client.beta.messages.tool_runner(
        model=opties.model,
        max_tokens=16000,
        max_iterations=opties.stappen,
        system=OPDRACHT,
        tools=gereedschappen(bank),
        thinking={"type": "adaptive"},
        output_config={"effort": "high"},
        cache_control={"type": "ephemeral"},
        # Oude tool-resultaten (stukken gelezen tekst) vallen weg als de context vol raakt.
        context_management={"edits": [{"type": "clear_tool_uses_20250919"}]},
        fallbacks="default",
        betas=["context-management-2025-06-27", "server-side-fallback-2026-07-01"],
        messages=[{"role": "user", "content":
                   f"Maak „{boek.get('titel')}” van {boek.get('auteur')} klaar. Begin met `overzicht`."}],
    )
    laatste = ""
    try:
        for bericht in runner:
            for blok in bericht.content:
                if blok.type == "text" and blok.text.strip():
                    laatste = blok.text.strip()
                    print(laatste, flush=True)
                elif blok.type == "tool_use":
                    argumenten = json.dumps(blok.input, ensure_ascii=False)
                    print(f"  → {blok.name}({argumenten[:100]}{'…' if len(argumenten) > 100 else ''})", flush=True)
            if bericht.stop_reason in ("refusal", "max_tokens"):
                print(f"Gestopt: {bericht.stop_reason}", flush=True)
    except (anthropic.AuthenticationError, TypeError) as fout:
        if isinstance(fout, TypeError) and "authentication" not in str(fout):
            raise
        sys.exit("Geen geldige API-sleutel: zet ANTHROPIC_API_KEY of log in met `ant auth login`.")
    except anthropic.APIConnectionError as fout:
        sys.exit(f"Geen verbinding met de API: {fout}")

    if laatste:
        bank.verslag("### Slotbericht van de agent\n\n" + laatste)
    print(f"\nKlaar. Lees {map_ / 'werkverslag.md'}, bekijk `git diff {opties.map}` en de PDF in {map_ / 'uit'}.")


if __name__ == "__main__":
    main(sys.argv)
