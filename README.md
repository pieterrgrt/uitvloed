# Uitvloed

uitvloed drukt Nederlandse literatuur opnieuw, maar pas als genoeg lezers erom vragen: elk boek krijgt een nummer in één doorlopende reeks, kost € 10 in pre-order en gaat naar de pers zodra er 500 bestellingen zijn. In deze werkplaats staan de teksten in `boeken/`, de Typst-sjablonen voor de A6-pocket in `sjablonen/` en de website voor uitvloed.nl in `site/` — alles onder versiebeheer, zodat elke wijziging bewaard blijft.

## De website

De site wordt gebouwd uit `site/reeks.json`, zonder extra pakketten:

```sh
node site/bouw.mjs                           # schrijft de pagina's naar site/_site/
python3 -m http.server -d site/_site 8000    # bekijk op http://localhost:8000
```

Een boek toevoegen of een teller bijwerken doe je in `site/reeks.json`. Vaste bestanden (stylesheet, CNAME) staan in `site/statisch/`. Bij elke push naar `main` bouwt GitHub de site en zet hem online.
