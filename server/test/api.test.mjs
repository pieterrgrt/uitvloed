import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import { mkdtempSync, writeFileSync, mkdirSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { openDatabase } from '../src/db.mjs';
import { maakApp } from '../src/app.mjs';

const boeken = [
  { nummer: 7, titel: 'De stille kade', auteur: 'Marieke Vondel', status: 'pre-order', preorders: 412 },
  { nummer: 6, titel: 'Nachtwacht in juli', auteur: 'Joost Berghuis', status: 'verschenen' },
];
const mails = [];
let server, basis, db;

before(async () => {
  const site = mkdtempSync(join(tmpdir(), 'uv-site-'));
  mkdirSync(join(site, 'reeks'));
  writeFileSync(join(site, 'index.html'), '<h1>Vandaag</h1>');
  writeFileSync(join(site, 'reeks', 'index.html'), '<h1>De reeks</h1>');
  writeFileSync(join(site, '404.html'), '<h1>Niet gevonden</h1>');
  db = openDatabase(':memory:');
  server = createServer();
  await new Promise((r) => server.listen(0, r));
  basis = `http://localhost:${server.address().port}`;
  const mailer = { async stuur(m) { mails.push(m); } };
  server.on('request', maakApp({ db, mailer, boeken, basisUrl: basis, siteMap: site }));
});
after(() => { server.close(); db.sluiten(); });

const post = (pad, body, { cookie, origin = basis, method = 'POST' } = {}) => fetch(basis + pad, {
  method, body: JSON.stringify(body),
  headers: { 'Content-Type': 'application/json', Origin: origin, ...(cookie ? { Cookie: cookie } : {}) },
});

async function inloggen(email) {
  const r = await post('/api/inloggen', { email, terug: '/reeks/07-de-stille-kade/' });
  assert.equal(r.status, 200);
  const token = /token=([\w-]+)/.exec(mails.at(-1).tekst)[1];
  const b = await post('/api/inloggen/bevestig', { token });
  assert.equal(b.status, 200);
  const data = await b.json();
  return { cookie: b.headers.get('set-cookie').split(';')[0], data, token };
}

test('levert de site en een 404-pagina', async () => {
  assert.match(await (await fetch(basis + '/')).text(), /Vandaag/);
  assert.match(await (await fetch(basis + '/reeks/')).text(), /De reeks/);
  const omleiding = await fetch(basis + '/reeks', { redirect: 'manual' });
  assert.equal(omleiding.status, 301);
  const weg = await fetch(basis + '/bestaat-niet/');
  assert.equal(weg.status, 404);
  assert.match(await weg.text(), /Niet gevonden/);
  assert.equal((await fetch(basis + '/%2e%2e/%2e%2e/etc/passwd')).status, 404);
});

test('tellers tonen alleen pre-orderboeken, met de startwaarde', async () => {
  assert.deepEqual(await (await fetch(basis + '/api/tellers')).json(), { 7: 412 });
});

test('inloggen met een link, pre-order plaatsen en annuleren', async () => {
  const { cookie, data, token } = await inloggen('Lezer@Voorbeeld.nl ');
  assert.equal(data.email, 'lezer@voorbeeld.nl');
  assert.equal(data.terug, '/reeks/07-de-stille-kade/');
  assert.match(mails.at(-1).html, /Inloggen/);

  // Een link werkt maar één keer.
  assert.equal((await post('/api/inloggen/bevestig', { token })).status, 400);

  const ik = await (await fetch(basis + '/api/ik', { headers: { Cookie: cookie } })).json();
  assert.deepEqual(ik.preorders, []);

  const p = await post('/api/preorders', { nummer: 7 }, { cookie });
  assert.equal(p.status, 201);
  assert.equal((await p.json()).teller, 413);
  const dubbel = await post('/api/preorders', { nummer: 7 }, { cookie });
  assert.equal(dubbel.status, 200);
  assert.equal((await dubbel.json()).teller, 413);

  const ik2 = await (await fetch(basis + '/api/ik', { headers: { Cookie: cookie } })).json();
  assert.equal(ik2.preorders[0].titel, 'De stille kade');
  assert.equal(ik2.preorders[0].pad, '/reeks/07-de-stille-kade/');

  const weg = await post('/api/preorders', { nummer: 7 }, { cookie, method: 'DELETE' });
  assert.equal((await weg.json()).teller, 412);

  const uit = await post('/api/uitloggen', {}, { cookie });
  assert.match(uit.headers.get('set-cookie'), /Max-Age=0/);
  assert.equal((await fetch(basis + '/api/ik', { headers: { Cookie: cookie } })).status, 401);
});

test('weigert pre-orders zonder inloggen, voor gesloten boeken en van andere sites', async () => {
  assert.equal((await post('/api/preorders', { nummer: 7 })).status, 401);
  const { cookie } = await inloggen('tweede@voorbeeld.nl');
  assert.equal((await post('/api/preorders', { nummer: 6 }, { cookie })).status, 409);
  assert.equal((await post('/api/preorders', { nummer: 99 }, { cookie })).status, 404);
  assert.equal((await post('/api/preorders', { nummer: 7 }, { cookie, origin: 'https://kwaadaardig.example' })).status, 403);
});

test('controleert e-mailadres, terugadres en aantal pogingen', async () => {
  assert.equal((await post('/api/inloggen', { email: 'geen-adres' })).status, 400);
  await post('/api/inloggen', { email: 'derde@voorbeeld.nl', terug: 'https://kwaadaardig.example/' });
  const token = /token=([\w-]+)/.exec(mails.at(-1).tekst)[1];
  const { terug } = await (await post('/api/inloggen/bevestig', { token })).json();
  assert.equal(terug, '/account/');

  let laatste;
  for (let i = 0; i < 4; i++) laatste = await post('/api/inloggen', { email: 'vierde@voorbeeld.nl' });
  assert.equal(laatste.status, 429);
});
