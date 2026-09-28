# uitvloed live zetten op Hetzner

Dit stappenplan zet uitvloed.nl op dezelfde Hetzner-server als liveaux en alduslab, op dezelfde manier: de app draait in Docker op een interne poort, nginx stuurt het domein daarheen en regelt HTTPS, en de DNS staat bij Mijndomein.

## Wat uitvloed gebruikt

| Website | Domein | Interne poort | Map op de server | Repository |
| --- | --- | --- | --- | --- |
| uitvloed | uitvloed.nl (www stuurt door) | 8002 | ~/uitvloed | github.com/pieterrgrt/uitvloed |

Zet deze regel ook in je overzicht van alle sites. Poort 8002 is de volgende vrije in dat overzicht. Controleer of hij echt vrij is voordat je begint:

```bash
sudo ss -tlnp | grep 127.0.0.1:8002
```

Geen uitvoer = vrij. Is hij bezet, kies dan een andere poort en pas die aan in `docker-compose.yml` en in stap 6.

**Anders dan bij liveaux**

- Eén container, geen aparte database: de gegevens staan in een SQLite-bestand in het Docker-volume `data`.
- Geen Django: geen `createsuperuser`, geen `/admin/`. Lezers maken zelf een account door in te loggen met een link per e-mail.
- `www.uitvloed.nl` stuurt door naar `uitvloed.nl`. De app accepteert inloggen en bestellen alleen vanaf `https://uitvloed.nl`.

## Stappenplan

Stap 1 is al gedaan in de code. Stap 2 gebeurt bij Mijndomein, stap 8 op GitHub, de rest op de server (`ssh root@178.105.62.224`).

1. **App klaarmaken (al gedaan).** De repository heeft een `Dockerfile`, een `docker-compose.yml` die alleen `127.0.0.1:8002` publiceert, en een `.env.example`.

2. **DNS bij Mijndomein.** Op dit moment wijst uitvloed.nl nog naar GitHub Pages. Pas de records voor `@` en `www` aan:
   - `@`: één A-record naar `178.105.62.224`. Verwijder de andere A-records (`185.199.108.153` t/m `185.199.111.153`).
   - `www`: verwijder de CNAME naar `pieterrgrt.github.io` en zet er een A-record naar `178.105.62.224` voor in de plaats.
   - Verwijder elk AAAA-record voor `@` en `www` (ook die van GitHub, `2606:50c0:…`), en elke doorverwijzing of gekoppeld pakket.
   - Laat de records voor andere namen staan, zoals `aldus`.

   Controleer vanaf de server:

   ```bash
   NS=$(dig +short NS uitvloed.nl | head -1); for p in "" "www."; do n="${p}uitvloed.nl"; for t in A AAAA CNAME; do echo "$n $t: $(dig +short $t $n @$NS)"; done; done
   ```

   Goed = beide A-regels tonen alleen `178.105.62.224`, en de AAAA- en CNAME-regels zijn leeg.

3. **Code ophalen.**

   ```bash
   git clone https://github.com/pieterrgrt/uitvloed.git ~/uitvloed
   cd ~/uitvloed
   ```

   Privé repository: gebruik een GitHub-token als wachtwoord.

4. **Instellingen invullen.**

   ```bash
   cp .env.example .env
   nano .env                 # opslaan: Ctrl+O, Enter; sluiten: Ctrl+X
   ```

   - `UV_BASIS_URL=https://uitvloed.nl` laten staan.
   - `SMTP_URL`: de SMTP-gegevens van de mailbox waaruit de inlogmails komen, als `smtp://gebruiker:wachtwoord@mailserver:587`. Nog geen mailbox? **Laat het leeg.** De inloglinks verschijnen dan in het logboek (stap 5), en inloggen werkt voor jou al wel.
   - `UV_AFZENDER`: het adres waar de mail vandaan komt; moet bij die mailbox horen.
   - `UV_ACHTER_PROXY=1` laten staan (de app zit achter nginx).

   Er zijn geen geheime sleutels of databasewachtwoorden nodig.

5. **Starten en testen.**

   ```bash
   docker compose up -d --build
   curl -sI http://127.0.0.1:8002/ | head -1
   curl -s http://127.0.0.1:8002/api/tellers
   ```

   Goed = `HTTP/1.1 200 OK` en een regel als `{"7":412,"9":205}`. Een Host-header is niet nodig: deze app accepteert elk domein.

6. **nginx laten doorsturen.** Maak `/etc/nginx/sites-available/uitvloed` met deze twee blokken:

   ```nginx
   server {
       listen 80;
       server_name www.uitvloed.nl;
       return 301 https://uitvloed.nl$request_uri;
   }

   server {
       listen 80;
       server_name uitvloed.nl;
       client_max_body_size 16k;
       location / {
           proxy_pass http://127.0.0.1:8002;
           proxy_set_header Host $host;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }
   }
   ```

   Zet hem aan en herlaad:

   ```bash
   sudo ln -s /etc/nginx/sites-available/uitvloed /etc/nginx/sites-enabled/uitvloed
   sudo nginx -t && sudo systemctl reload nginx
   ```

7. **HTTPS aanvragen.** Pas als stap 2 klopt:

   ```bash
   sudo certbot --nginx -d uitvloed.nl -d www.uitvloed.nl
   ```

   Kies "redirect" als certbot erom vraagt. Open daarna `https://uitvloed.nl`.

8. **GitHub Pages uitzetten.** Op GitHub: repository → **Settings → Pages**. Haal `uitvloed.nl` weg bij *Custom domain* en kies **Unpublish site**. De oude tijdelijke pagina verdwijnt dan ook bij GitHub.

9. **Inloggen testen.** Ga naar `https://uitvloed.nl/account/`, vul je eigen e-mailadres in en klik op de link in de mail. Staat `SMTP_URL` nog leeg, haal de link dan uit het logboek:

   ```bash
   docker compose logs web | grep token= | tail -1
   ```

   Open die link in dezelfde browser. Reserveer daarna een boek en kijk of het onder Mijn account staat.

## Valkuilen

| Wat je ziet | Oorzaak | Oplossing |
| --- | --- | --- |
| GitHub-pagina of 404 van GitHub op uitvloed.nl | Er staat nog een A-, AAAA- of CNAME-record van GitHub, of je computer onthoudt de oude DNS | Stap 2 opnieuw controleren; op de Mac `sudo dscacheutil -flushcache; sudo killall -HUP mDNSResponder` |
| Certbot: `unauthorized … 404` met een IPv6-adres | Een AAAA-record wijst nog naar GitHub of Mijndomein | AAAA-records verwijderen, certbot opnieuw |
| Nextcloud-pagina op uitvloed.nl | Nog geen HTTPS-blok voor uitvloed; nginx valt terug op het eerste | Stap 7 |
| "Verzoek van onbekende herkomst" bij inloggen of bestellen | Je zit op www of op http, of `UV_BASIS_URL` klopt niet | Gebruik `https://uitvloed.nl`; controleer `.env` en daarna `docker compose up -d` |
| "Er ging iets mis" na het versturen van het inlogformulier | Mail versturen mislukt: verkeerde `SMTP_URL` | `docker compose logs web` toont de fout. `SMTP_URL` leeg laten tot het werkt |
| "Te veel pogingen" | Meer dan 3 inlogaanvragen per adres of 10 per IP-adres in 15 minuten | Een kwartier wachten, of `docker compose restart web` (zet de teller op nul) |
| Container start niet, `address already in use` | Poort 8002 is al bezet | Andere poort kiezen in `docker-compose.yml` en in het nginx-blok |

## Beheer

Alle commando's in `~/uitvloed`.

| Wat | Commando |
| --- | --- |
| Nieuwe versie live zetten | `./deploy/update.sh` |
| Draait alles? | `docker compose ps` |
| Foutmeldingen bekijken | `docker compose logs -f web` (stoppen: Ctrl+C) |
| Back-up van de database | `docker compose exec web node server/src/backup.mjs` |
| Back-up naar de server kopiëren | `docker compose cp web:/data/backups/ ./backups/` |
| Boek toevoegen of teller aanpassen | `site/reeks.json` wijzigen op GitHub, dan `./deploy/update.sh` |
| nginx-config testen na een wijziging | `sudo nginx -t && sudo systemctl reload nginx` |
| Certificaten controleren | `sudo certbot certificates` |

De database staat in het Docker-volume `uitvloed_data`. `docker compose down` laat dat volume staan; `docker compose down -v` gooit alle accounts en pre-orders weg.
