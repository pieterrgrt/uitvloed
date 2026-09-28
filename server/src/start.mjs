// Start de server van uitvloed. Instellingen via omgevingsvariabelen (zie .env.voorbeeld).
import { createServer } from 'node:http';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { openDatabase } from './db.mjs';
import { maakMailer } from './mail.mjs';
import { maakApp } from './app.mjs';

const standaard = (rel) => fileURLToPath(new URL(rel, import.meta.url));
const env = process.env;
const poort = Number(env.PORT ?? 3000);
const basisUrl = env.UV_BASIS_URL ?? `http://localhost:${poort}`;
const siteMap = env.UV_SITE ?? standaard('../../site/_site');
const reeks = JSON.parse(readFileSync(env.UV_REEKS ?? standaard('../../site/reeks.json'), 'utf8'));
const db = openDatabase(env.UV_DATABASE ?? standaard('../data/uitvloed.db'));
const mailer = maakMailer({ smtpUrl: env.SMTP_URL, afzender: env.UV_AFZENDER ?? 'uitvloed <post@uitvloed.nl>' });

if (!env.SMTP_URL) console.log('Geen SMTP_URL ingesteld: inloglinks verschijnen hier in het logboek in plaats van per e-mail.');

db.opruimen();
setInterval(() => db.opruimen(), 60 * 60 * 1000).unref();

const server = createServer(maakApp({ db, mailer, boeken: reeks.boeken, basisUrl, siteMap, vertrouwProxy: env.UV_ACHTER_PROXY === '1' }));
server.listen(poort, () => console.log(`uitvloed draait op ${basisUrl} (poort ${poort})`));

for (const sig of ['SIGINT', 'SIGTERM']) {
  process.on(sig, () => server.close(() => { db.sluiten(); process.exit(0); }));
}
