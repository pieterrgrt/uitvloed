# Uitvloed

uitvloed drukt Nederlandse literatuur opnieuw, maar pas als genoeg lezers erom vragen: elk boek krijgt een nummer in één doorlopende reeks, kost € 10 in pre-order en gaat naar de pers zodra er 500 bestellingen zijn. In deze werkplaats staan de teksten in `boeken/`, de Typst-sjablonen voor de A6-pocket in `sjablonen/` en de website voor uitvloed.nl in `site/` — alles onder versiebeheer, zodat elke wijziging bewaard blijft.

## De website

De site staat in `site/` en wordt gebouwd uit `site/reeks.json`. De server in `server/` levert die pagina's en regelt het inloggen (met een link per e-mail) en de pre-orders.

```sh
node site/bouw.mjs      # bouwt de pagina's naar site/_site/
cd server && npm install && npm start    # http://localhost:3000
```

Een boek toevoegen of een teller aanpassen doe je in `site/reeks.json`. Hoe de server werkt en hoe je hem online zet staat in `server/README.md`. Bij elke pull request bouwt GitHub de site en draait de servertests.
