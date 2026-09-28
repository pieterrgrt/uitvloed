# Uitvloed

uitvloed drukt Nederlandse literatuur opnieuw, maar pas als genoeg lezers erom vragen: elk boek krijgt een nummer in één doorlopende reeks, kost € 10 in pre-order en gaat naar de pers zodra er 500 bestellingen zijn. In deze werkplaats staan de teksten in `boeken/`, de Typst-sjablonen voor de A6-pocket in `sjablonen/`, de scripts die er drukklare PDF's van maken in `gereedschap/` en de website voor uitvloed.nl in `site/` — alles onder versiebeheer, zodat elke wijziging bewaard blijft.

## De website

De site staat in `site/` en is een [Eleventy](https://www.11ty.dev/)-project. Elk boek heeft een eigen gegevensbestand in `site/boeken/`; daaruit maakt Eleventy de homepage, de catalogus (`/reeks/`) en per titel een boekpagina (`/reeks/07-de-stille-kade/`). De server in `server/` levert die pagina's en regelt het inloggen (met een link per e-mail) en de pre-orders.

```sh
cd site && npm install
npm start               # bouwt en ververst bij elke wijziging: http://localhost:8080
npm run build           # bouwt de pagina's naar site/_site/
cd ../server && npm install && npm start    # site + inloggen + pre-orders: http://localhost:3000
```

Wat waar staat:

| pad | inhoud |
| --- | --- |
| `site/boeken/<nr>-<titel>.json` | één bestand per boek |
| `site/reeks.json` | instellingen van de reeks: het uitgelichte boek op de homepage, het doel (500) en de thema's |
| `site/src/` | sjablonen: `_includes/basis.njk` (kop en voet), `_includes/bouwstenen.njk` (kaft, vraagmeter, catalogusitem), `index.njk`, `reeks/index.njk` (catalogus), `reeks/boek.njk` (boekpagina) |
| `site/statisch/` | vaste bestanden (stylesheet, script), komen ongewijzigd in de site |

**Een boek toevoegen:** kopieer een bestand in `site/boeken/`, geef het het volgende nummer en pas de velden aan. De bestandsnaam is vrij, maar houd `<nr>-<titel>.json` aan zodat de map op volgorde staat. Het adres van de boekpagina volgt uit nummer en titel.

| veld | betekenis |
| --- | --- |
| `nummer` | nummer in de reeks (verplicht, uniek) |
| `titel`, `auteur` | verplicht |
| `jaar` | jaar van de eerste druk (verplicht); komt ook in het colofon als „Eerste druk: …” |
| `kort` | één zin over het boek, voor de homepage, de boekpagina en zoekmachines (verplicht) |
| `tekst` | langere tekst in alinea's (lijst); ook de achterflap van het gedrukte boek |
| `status` | `pre-order`, `binnenkort`, `verschenen` of `uitverkocht` |
| `preorders` | bestellingen van vóór de server; de server telt de echte reserveringen erbij op |
| `bestellink` | waar een verschenen boek te bestellen is; zonder link toont de pagina alleen de status. Pre-orders lopen via de eigen knop op de boekpagina |
| `kleur` | kleur van de kaft, een token uit `uitvloed.css` (`reeks-07`) |
| `genre`, `gegevens` | optioneel: genre boven de titel en een tabel met formaat, pagina's enz. |

Klopt er iets niet (veld vergeten, nummer dubbel, onbekende status), dan stopt de bouw met een melding welk bestand het is. Bij elke pull request bouwt GitHub de site en draait de servertests.

## Een boek zetten

Van ruwe brontekst naar drukklare PDF's in drie stappen. Eenmalig: `pip install -r gereedschap/requirements.txt` (Typst als Python-pakket; de lettertypes staan in `sjablonen/letters/`).

1. **Brontekst neerzetten.** Maak `boeken/<titel>/` met de ruwe tekst als `bron.txt` en een `boek.json`. Staat het boek al in `site/boeken/`, dan is `{"nummer": 9}` genoeg: titel, auteur, kleur, achterflaptekst en het jaar van de eerste druk komen dan van de site. Kijk naar `boeken/_proef/` voor alle velden.
2. **Opschonen.** `python3 gereedschap/opschonen.py boeken/<titel>` haalt paginanummers, afbreekstreepjes en losse witregels weg, krult aanhalingstekens en schrijft `tekst.txt`. Controleer `afbrekingen.txt` (heelgemaakte woorden) en corrigeer daarna in `tekst.txt` — die wordt niet meer overschreven, tenzij je `--opnieuw` meegeeft.
3. **Zetten.** `python3 gereedschap/bouw.py boeken/<titel>` schrijft naar `boeken/<titel>/uit/`:
   - `binnenwerk.pdf` — A6 (105 × 148 mm), EB Garamond, aangevuld tot een veelvoud van vier pagina's;
   - `omslag.pdf` — achterkant, rug en voorkant met 3 mm afloop; de rugdikte volgt uit het aantal pagina's × `papierdikte_mm`.

   Met `--hulplijnen` komt er een omslag met snijrand en rug erbij, met `--voorbeeld` PNG's om snel te kijken.

Instellingen in `boek.json`:

| veld | betekenis |
| --- | --- |
| `nummer` | nummer in de reeks; koppelt aan het boekbestand in `site/boeken/` |
| `titel`, `auteur`, `kleur`, `achterflap` | overschrijven wat de site zegt (`kleur` is een token uit `uitvloed.css`, bijv. `reeks-07`) |
| `oorspronkelijk` | regel voor het colofon, bijv. „Eerste druk: Amsterdam, 1887.”; standaard „Eerste druk: <jaar van de site>.” |
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
Een boek toevoegen of een teller aanpassen doe je in `site/boeken/`. Hoe de server werkt en hoe je hem online zet staat in `server/README.md`. Bij elke pull request bouwt GitHub de site en draait de servertests.
