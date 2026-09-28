# Uitvloed

uitvloed drukt Nederlandse literatuur opnieuw, maar pas als genoeg lezers erom vragen: elk boek krijgt een nummer in één doorlopende reeks, kost € 10 in pre-order en gaat naar de pers zodra er 500 bestellingen zijn. In deze werkplaats staan de teksten in `boeken/`, de Typst-sjablonen voor de A6-pocket in `sjablonen/`, de scripts die er drukklare PDF's van maken in `gereedschap/` en de website voor uitvloed.nl in `site/` — alles onder versiebeheer, zodat elke wijziging bewaard blijft.

## De website

De site wordt gebouwd uit `site/reeks.json`, zonder extra pakketten:

```sh
node site/bouw.mjs                           # schrijft de pagina's naar site/_site/
python3 -m http.server -d site/_site 8000    # bekijk op http://localhost:8000
```

Een boek toevoegen of een teller bijwerken doe je in `site/reeks.json`. Vaste bestanden (stylesheet, CNAME) staan in `site/statisch/`. Bij elke push naar `main` bouwt GitHub de site en zet hem online.

## Een boek zetten

Van ruwe brontekst naar drukklare PDF's in drie stappen. Eenmalig: `pip install -r gereedschap/requirements.txt` (Typst als Python-pakket; de lettertypes staan in `sjablonen/letters/`).

1. **Brontekst neerzetten.** Maak `boeken/<titel>/` met de ruwe tekst als `bron.txt` en een `boek.json`. Staat het boek al in `site/reeks.json`, dan is `{"nummer": 9}` genoeg: titel, auteur, kleur en achterflaptekst komen dan van de site. Kijk naar `boeken/_proef/` voor alle velden.
2. **Opschonen.** `python3 gereedschap/opschonen.py boeken/<titel>` haalt paginanummers, afbreekstreepjes en losse witregels weg, krult aanhalingstekens en schrijft `tekst.txt`. Controleer `afbrekingen.txt` (heelgemaakte woorden) en corrigeer daarna in `tekst.txt` — die wordt niet meer overschreven, tenzij je `--opnieuw` meegeeft.
3. **Zetten.** `python3 gereedschap/bouw.py boeken/<titel>` schrijft naar `boeken/<titel>/uit/`:
   - `binnenwerk.pdf` — A6 (105 × 148 mm), EB Garamond, aangevuld tot een veelvoud van vier pagina's;
   - `omslag.pdf` — achterkant, rug en voorkant met 3 mm afloop; de rugdikte volgt uit het aantal pagina's × `papierdikte_mm`.

   Met `--hulplijnen` komt er een omslag met snijrand en rug erbij, met `--voorbeeld` PNG's om snel te kijken.

Instellingen in `boek.json`:

| veld | betekenis |
| --- | --- |
| `nummer` | nummer in de reeks; koppelt aan `site/reeks.json` |
| `titel`, `auteur`, `kleur`, `achterflap` | overschrijven wat de site zegt (`kleur` is een token uit `uitvloed.css`, bijv. `reeks-07`) |
| `oorspronkelijk` | regel voor het colofon, bijv. „Eerste druk: Amsterdam, 1887.” |
| `isbn` | komt in colofon en op de achterkant |
| `hoofdstukpatroon` | reguliere expressie voor hoofdstukkoppen in de bron |
| `weg` | lijst reguliere expressies voor regels die weg moeten (kopregels met titel of auteur) |
| `papierdikte_mm` | dikte van één vel (twee pagina's), op te vragen bij de drukker; standaard 0,1 |
| `rug_mm` | vaste rugdikte als de drukker die zelf opgeeft |

`python3 -m unittest discover gereedschap` test het opschoonscript; GitHub draait die tests en zet het proefboek bij elke wijziging.

## Proefdruk bestellen

Vraag bij de drukpartij na, en pas zo nodig `boek.json` of de sjablonen aan:

- **Formaat**: A6, 105 × 148 mm bijgesneden. Willen ze het binnenwerk met of zonder afloop? (Het binnenwerk heeft geen afloop nodig: niets loopt tot de rand.)
- **Paginatal**: veelvoud van vier is standaard; sommige drukkers willen 8 of 16.
- **Rug**: hun papierdikte of rekenformule, en of de omslag als één vel (zoals nu) of als losse voor- en achterkant moet.
- **Kleur**: Typst levert RGB. De meeste printing-on-demand-drukkers zetten dat zelf om naar CMYK; vraag of ze een PDF/X-bestand of een kleurprofiel eisen.
- **ISBN**: de achterkant houdt rechtsonder 36 × 22 mm vrij voor de streepjescode.

Bestel altijd eerst één proefdruk en controleer: marges bij de rug, rugtekst gecentreerd, kleur van de strook, afbrekingen.
