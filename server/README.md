# Server van uitvloed

Eén Node-programma dat de website levert én het inloggen en de pre-orders regelt. Het gebruikt de SQLite-database die in Node zit, en `nodemailer` voor de inlogmails.

## Lokaal draaien

```sh
(cd site && npm install && npm run build)   # vanuit de hoofdmap: bouwt de pagina's
cd server
npm install
npm start                   # http://localhost:3000
npm test                    # de tests
```

Zonder `SMTP_URL` worden inloglinks niet gemaild maar in de terminal gezet. Kopieer de link naar je browser om in te loggen.

## Hoe inloggen werkt

1. Iemand vult op `/account/` een e-mailadres in. De server maakt een willekeurige code, bewaart alleen de hash ervan en mailt een link: `https://uitvloed.nl/account/?token=…`.
2. De accountpagina stuurt die code terug naar de server. Die controleert de code (één keer bruikbaar, 15 minuten geldig), maakt zo nodig een account aan en zet een sessiecookie (`HttpOnly`, `Secure`, `SameSite=Lax`, 30 dagen).
3. Met die cookie kan de lezer pre-orders plaatsen en annuleren.

Wijzigende verzoeken worden alleen aangenomen als ze van `UV_BASIS_URL` komen. Het inlogformulier is beperkt tot 3 aanvragen per e-mailadres en 10 per IP-adres per kwartier.

## API

| Verzoek | Doet |
|---|---|
| `GET /api/tellers` | Aantal pre-orders per boek dat in pre-order is |
| `GET /api/ik` | Ingelogde lezer en diens pre-orders (401 als niet ingelogd) |
| `POST /api/inloggen` `{email, terug}` | Stuurt een inloglink |
| `POST /api/inloggen/bevestig` `{token}` | Wisselt de link in voor een sessie |
| `POST /api/uitloggen` | Beëindigt de sessie |
| `POST /api/preorders` `{nummer}` | Reserveert een boek |
| `DELETE /api/preorders` `{nummer}` | Annuleert de reservering |

De teller is `preorders` uit het boekbestand in `site/boeken/` (bestellingen van vóór de server) plus de reserveringen in de database. Zet `preorders` op 0 als je alleen echte reserveringen wilt tellen.

## Online zetten

Voor de Hetzner-server met nginx en Mijndomein: volg `deploy/LIVE-ZETTEN.md`. In het algemeen:

De `Dockerfile` in de hoofdmap bouwt de site en start de server. Elke host die een container kan draaien werkt (Fly.io, Render, Railway, een eigen VPS met Docker). Nodig:

- de instellingen uit `.env.example`, zie `.env.example` in de hoofdmap;
- een blijvende schijf op `/data` voor de database, met back-ups;
- https ervoor (de meeste hosts regelen dat; op een eigen VPS bijvoorbeeld Caddy), en dan `UV_ACHTER_PROXY=1`;
- de DNS van `uitvloed.nl` naar die host in plaats van naar GitHub Pages.
