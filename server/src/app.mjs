// De server van uitvloed: levert de gebouwde site en de API voor inloggen en pre-orders.
import { createHash, randomBytes } from 'node:crypto';
import { readFile, stat } from 'node:fs/promises';
import { extname, join, normalize, sep } from 'node:path';
import { inlogmail } from './mail.mjs';

const LINK_GELDIG_MS = 15 * 60 * 1000;
const SESSIE_GELDIG_MS = 30 * 24 * 60 * 60 * 1000;
const MAX_BODY = 4 * 1024;
const COOKIE = 'uv_sessie';
const EMAIL = /^[^\s@]{1,64}@[^\s@]{1,190}\.[^\s@]{2,}$/;

const TYPES = {
  '.html': 'text/html; charset=utf-8', '.css': 'text/css; charset=utf-8', '.js': 'text/javascript; charset=utf-8',
  '.json': 'application/json', '.svg': 'image/svg+xml', '.png': 'image/png', '.jpg': 'image/jpeg',
  '.webp': 'image/webp', '.ico': 'image/x-icon', '.woff2': 'font/woff2', '.ttf': 'font/ttf', '.txt': 'text/plain; charset=utf-8',
};

const hash = (s) => createHash('sha256').update(s).digest('hex');
const token = () => randomBytes(32).toString('base64url');
// Zelfde adres als site/bouw.mjs maakt: /reeks/07-de-stille-kade/
const boekPad = (b) => `/reeks/${String(b.nummer).padStart(2, '0')}-${b.titel.toLowerCase()
  .normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '')}/`;

class Fout extends Error {
  constructor(status, melding) { super(melding); this.status = status; }
}

// Eenvoudige teller per sleutel (IP of e-mailadres) om misbruik van het inlogformulier te beperken.
function maakRemmer(max, vensterMs) {
  const pogingen = new Map();
  return (sleutel) => {
    const nu = Date.now();
    const lijst = (pogingen.get(sleutel) ?? []).filter((t) => nu - t < vensterMs);
    if (lijst.length >= max) return false;
    lijst.push(nu);
    pogingen.set(sleutel, lijst);
    if (pogingen.size > 10000) pogingen.clear();
    return true;
  };
}

function leesCookie(req, naam) {
  for (const deel of (req.headers.cookie ?? '').split(';')) {
    const [k, ...v] = deel.trim().split('=');
    if (k === naam) return v.join('=');
  }
  return null;
}

async function leesJson(req) {
  if (!(req.headers['content-type'] ?? '').startsWith('application/json')) throw new Fout(415, 'Stuur JSON.');
  let body = '';
  for await (const stuk of req) {
    body += stuk;
    if (body.length > MAX_BODY) throw new Fout(413, 'Verzoek te groot.');
  }
  try { return JSON.parse(body || '{}'); } catch { throw new Fout(400, 'Ongeldige JSON.'); }
}

function stuurJson(res, status, data, headers = {}) {
  res.writeHead(status, { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store', ...headers });
  res.end(JSON.stringify(data));
}

// Alleen een pad binnen de eigen site mag als terugadres dienen.
const veiligTerug = (t) => (typeof t === 'string' && /^\/(?!\/)[\w\-./]*$/.test(t) && !t.includes('..') ? t : '/account/');

export function maakApp({ db, mailer, boeken, basisUrl, siteMap, vertrouwProxy = false }) {
  const basis = new URL(basisUrl);
  const veilig = basis.protocol === 'https:';
  const perIp = maakRemmer(10, 15 * 60 * 1000);
  const perEmail = maakRemmer(3, 15 * 60 * 1000);
  const boekVan = new Map(boeken.map((b) => [b.nummer, b]));

  const sessieCookie = (waarde, maxAge) =>
    `${COOKIE}=${waarde}; Path=/; HttpOnly; SameSite=Lax; Max-Age=${maxAge}${veilig ? '; Secure' : ''}`;

  function gebruikerVan(req) {
    const t = leesCookie(req, COOKIE);
    return t ? db.sessieZoeken(hash(t)) : undefined;
  }
  function vereisGebruiker(req) {
    const g = gebruikerVan(req);
    if (!g) throw new Fout(401, 'Log eerst in.');
    return g;
  }
  function tellers() {
    const uitDb = db.tellers();
    return Object.fromEntries(boeken.filter((b) => b.status === 'pre-order')
      .map((b) => [b.nummer, (b.preorders ?? 0) + (uitDb[b.nummer] ?? 0)]));
  }

  const routes = {
    'GET /api/tellers': () => [200, tellers()],

    'GET /api/ik': (req) => {
      const g = vereisGebruiker(req);
      const preorders = db.preordersVan(g.id).map((p) => {
        const b = boekVan.get(p.boek);
        return { nummer: p.boek, titel: b?.titel ?? `№ ${p.boek}`, auteur: b?.auteur ?? '', pad: b ? boekPad(b) : '/reeks/', geplaatst: p.geplaatst };
      });
      return [200, { email: g.email, preorders }];
    },

    'POST /api/inloggen': async (req) => {
      const { email, terug } = await leesJson(req);
      const adres = typeof email === 'string' ? email.trim().toLowerCase() : '';
      if (!EMAIL.test(adres)) throw new Fout(400, 'Vul een geldig e-mailadres in.');
      const ip = (vertrouwProxy && String(req.headers['x-forwarded-for'] ?? '').split(',')[0].trim()) || req.socket.remoteAddress || '';
      if (!perIp(ip) || !perEmail(adres)) throw new Fout(429, 'Te veel pogingen. Probeer het over een kwartier opnieuw.');
      const t = token();
      db.linkOpslaan(hash(t), adres, veiligTerug(terug), Date.now() + LINK_GELDIG_MS);
      const link = new URL(`/account/?token=${t}`, basis).href;
      await mailer.stuur({ aan: adres, ...inlogmail(link) });
      return [200, { ok: true }];
    },

    'POST /api/inloggen/bevestig': async (req) => {
      const { token: t } = await leesJson(req);
      const link = typeof t === 'string' ? db.linkPakken(hash(t)) : undefined;
      if (!link || link.verloopt < Date.now()) throw new Fout(400, 'Deze link is verlopen of al gebruikt. Vraag een nieuwe aan.');
      const g = db.gebruikerVoor(link.email);
      const sessie = token();
      db.sessieOpslaan(hash(sessie), g.id, Date.now() + SESSIE_GELDIG_MS);
      return [200, { email: g.email, terug: link.terug }, { 'Set-Cookie': sessieCookie(sessie, SESSIE_GELDIG_MS / 1000) }];
    },

    'POST /api/uitloggen': (req) => {
      const t = leesCookie(req, COOKIE);
      if (t) db.sessieWissen(hash(t));
      return [200, { ok: true }, { 'Set-Cookie': sessieCookie('', 0) }];
    },

    'POST /api/preorders': async (req) => {
      const g = vereisGebruiker(req);
      const { nummer } = await leesJson(req);
      const b = boekVan.get(nummer);
      if (!b) throw new Fout(404, 'Dit boek bestaat niet.');
      if (b.status !== 'pre-order') throw new Fout(409, 'Voor dit boek is pre-order niet open.');
      const nieuw = db.preorderPlaatsen(g.id, nummer);
      return [nieuw ? 201 : 200, { nummer, geplaatst: true, teller: tellers()[nummer] }];
    },

    'DELETE /api/preorders': async (req) => {
      const g = vereisGebruiker(req);
      const { nummer } = await leesJson(req);
      const b = boekVan.get(nummer);
      if (!b || b.status !== 'pre-order') throw new Fout(409, 'Deze pre-order kan niet meer worden geannuleerd.');
      db.preorderAnnuleren(g.id, nummer);
      return [200, { nummer, geplaatst: false, teller: tellers()[nummer] }];
    },
  };

  async function api(req, res, pad) {
    // Wijzigende verzoeken moeten van de eigen site komen (tegen cross-site request forgery).
    if (req.method !== 'GET' && req.headers.origin !== basis.origin) throw new Fout(403, 'Verzoek van onbekende herkomst.');
    const route = routes[`${req.method} ${pad}`];
    if (!route) throw new Fout(404, 'Onbekend adres.');
    const [status, data, headers] = await route(req);
    stuurJson(res, status, data, headers);
  }

  async function bestand(req, res, pad) {
    if (req.method !== 'GET' && req.method !== 'HEAD') throw new Fout(405, 'Niet toegestaan.');
    let rel;
    try { rel = normalize(decodeURIComponent(pad)).replace(/^([/\\])+/, ''); } catch { throw new Fout(400, 'Ongeldig pad.'); }
    let doel = join(siteMap, rel);
    if (doel !== siteMap && !doel.startsWith(siteMap + sep)) throw new Fout(404, 'Niet gevonden.');
    let info = await stat(doel).catch(() => null);
    if (info?.isDirectory()) {
      if (!pad.endsWith('/')) { res.writeHead(301, { Location: pad + '/' }); return res.end(); }
      doel = join(doel, 'index.html');
      info = await stat(doel).catch(() => null);
    }
    if (!info?.isFile()) throw new Fout(404, 'Niet gevonden.');
    const type = TYPES[extname(doel)] ?? 'application/octet-stream';
    res.writeHead(200, {
      'Content-Type': type,
      'Cache-Control': type.startsWith('text/html') ? 'no-cache' : 'public, max-age=3600',
      'X-Content-Type-Options': 'nosniff',
    });
    res.end(req.method === 'HEAD' ? undefined : await readFile(doel));
  }

  return async function verwerk(req, res) {
    const pad = new URL(req.url, basis).pathname;
    try {
      if (pad === '/api' || pad.startsWith('/api/')) await api(req, res, pad);
      else await bestand(req, res, pad);
    } catch (e) {
      const status = e instanceof Fout ? e.status : 500;
      if (status === 500) console.error(e);
      const melding = status === 500 ? 'Er ging iets mis. Probeer het later opnieuw.' : e.message;
      if (pad.startsWith('/api')) return stuurJson(res, status, { fout: melding });
      if (status === 404) {
        const html = await readFile(join(siteMap, '404.html')).catch(() => null);
        if (html) { res.writeHead(404, { 'Content-Type': TYPES['.html'] }); return res.end(html); }
      }
      res.writeHead(status, { 'Content-Type': 'text/plain; charset=utf-8' });
      res.end(melding);
    }
  };
}
