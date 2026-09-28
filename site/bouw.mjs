// Bouwt de website van uitvloed uit reeks.json naar site/_site/.
// Gebruik: node site/bouw.mjs
import { readFileSync, writeFileSync, mkdirSync, rmSync, cpSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const hier = dirname(fileURLToPath(import.meta.url));
const uit = join(hier, '_site');
const data = JSON.parse(readFileSync(join(hier, 'reeks.json'), 'utf8'));
const DOEL = data.doel;
const JAAR = new Date().getFullYear();
const SLOGAN = 'Nederlandse literatuur, opnieuw gedrukt — pas als jij het bestelt.';

const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]);
const nr = (n) => '№ ' + String(n).padStart(2, '0');
const slug = (b) => String(b.nummer).padStart(2, '0') + '-' + b.titel.toLowerCase()
  .normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
const boeken = [...data.boeken].sort((a, b) => b.nummer - a.nummer);
const pct = (b) => Math.min(100, Math.round((b.preorders / DOEL) * 100));

const STATUS = {
  'pre-order': (b) => `Pre-order · ${pct(b)}%`,
  verschenen: () => 'Verschenen · € 10',
  binnenkort: () => 'Binnenkort',
  uitverkocht: () => 'Uitverkocht',
};
const FILTERS = [['pre-order', 'In pre-order'], ['verschenen', 'Verschenen'], ['binnenkort', 'Binnenkort']];

function pagina({ pad, titel, beschrijving, actief, inhoud, bestand = 'index.html' }) {
  const r = '/';
  const links = [['', 'Vandaag'], ['reeks/', 'De reeks'], ['verkennen/', 'Verkennen'], ['over/', 'Over uitvloed']];
  const html = `<!doctype html>
<html lang="nl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${esc(titel)}</title>
<meta name="description" content="${esc(beschrijving)}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=EB+Garamond:ital,wght@0,400;0,500;0,600;1,400;1,500&display=swap">
<link rel="stylesheet" href="${r}uitvloed.css">
<script src="${r}uitvloed.js" defer></script>
</head>
<body>
<a class="skip" href="#inhoud">Naar de inhoud</a>
<header class="uv-nav">
  <div class="wrap uv-nav-in">
    <a class="uv-wordmark" href="${r}">uitvloed</a>
    <nav class="uv-nav-links" aria-label="Hoofdmenu">
      ${links.map(([p, t]) => `<a href="${r}${p}"${actief === t ? ' aria-current="page"' : ''}>${t}</a>`).join('\n      ')}
    </nav>
    <a class="uv-btn uv-btn-sm" href="${r}account/" data-account>Aanmelden</a>
  </div>
</header>
<main id="inhoud">
${inhoud(r)}
</main>
<footer class="uv-footer">
  <div class="wrap uv-footer-in">
    <span class="uv-wordmark">uitvloed</span>
    <span class="uv-footer-line">${SLOGAN}</span>
    <span class="uv-footer-meta">© ${JAAR}</span>
  </div>
</footer>
</body>
</html>
`;
  const map = join(uit, pad);
  mkdirSync(map, { recursive: true });
  writeFileSync(join(map, bestand), html);
}

const kaftGroot = (b, groot = false) => `<div class="uv-cover${groot ? ' uv-cover-lg' : ''}" style="--reeks: var(--${b.kleur})" role="img" aria-label="Kaft van ${esc(b.titel)} door ${esc(b.auteur)}">
  <div class="uv-cover-strip"><span>uitvloed</span><span class="uv-no">${nr(b.nummer)}</span></div>
  <div class="uv-cover-body">
    <div><div class="uv-cover-rule"></div><div class="uv-cover-title">${esc(b.titel)}</div></div>
    <div class="uv-cover-author">${esc(b.auteur)}</div>
  </div>
</div>`;

const item = (b, r) => `<a class="uv-item" href="${r}reeks/${slug(b)}/" data-status="${b.status}">
  <div class="uv-cover uv-cover-sm" style="--reeks: var(--${b.kleur})">
    <div class="uv-cover-strip"><span>uitvloed</span><span class="uv-no">${nr(b.nummer)}</span></div>
    <div class="uv-cover-body"><div class="uv-cover-title">${esc(b.titel)}</div><div class="uv-cover-author">${esc(b.auteur)}</div></div>
  </div>
  <div class="uv-item-status${b.status === 'pre-order' ? ' is-open' : ''}">${STATUS[b.status](b)}</div>
</a>`;

const meter = (b, r, volledig) => {
  const nog = Math.max(0, DOEL - b.preorders);
  return `<div class="uv-card uv-meter" data-teller="${b.nummer}" data-doel="${DOEL}">
  <div class="uv-meter-head">
    <div class="uv-meter-count"><span class="uv-meter-dot" aria-hidden="true"></span><span><span data-aantal>${b.preorders}</span> <small>pre-orders</small></span></div>
    <span class="uv-meter-goal">doel ${DOEL}</span>
  </div>
  <div class="uv-meter-track" role="progressbar" aria-label="Pre-orders voor ${esc(b.titel)}" aria-valuemin="0" aria-valuemax="${DOEL}" aria-valuenow="${b.preorders}" data-balk><div class="uv-meter-fill" style="width: ${pct(b)}%" data-vulling></div></div>
  <div class="uv-meter-note" data-notitie>${nog ? `Nog ${nog} lezers en de persen draaien.` : 'Het doel is gehaald. De persen draaien.'}</div>${volledig ? `
  <div class="uv-price"><strong>€ 10</strong><span>paperback · incl. verzending</span></div>
  <button type="button" class="uv-btn uv-btn-block" data-preorder="${b.nummer}">Pre-order · € 10</button>
  <button type="button" class="uv-btn uv-btn-secondary uv-btn-block" data-annuleer="${b.nummer}" hidden>Annuleer pre-order</button>
  <p class="uv-melding" data-melding="${b.nummer}" role="status"></p>` : ''}
</div>`;
};

const stappen = `<section class="uv-card uv-steps" id="pre-order" aria-labelledby="stappen-kop">
  <h2 class="uv-eyebrow" id="stappen-kop" style="margin:0">Zo werkt pre-order bij uitvloed</h2>
  <ol class="uv-steps-grid">
    <li><div class="uv-step-no">1.</div><div class="uv-step-text">Reserveer je exemplaar voor een tientje.</div></li>
    <li><div class="uv-step-no">2.</div><div class="uv-step-text">Bij ${DOEL} pre-orders drukken we de oplage — nooit meer dan nodig.</div></li>
    <li><div class="uv-step-no">3.</div><div class="uv-step-text">Binnen drie weken op je mat, genummerd in de reeks.</div></li>
  </ol>
</section>`;

const themaKaarten = data.themas.map((t) => `<div class="uv-card uv-theme" style="--reeks: var(--${t.kleur})"><div class="uv-theme-swatch" aria-hidden="true"></div><h3 class="uv-theme-title" style="margin:0">${esc(t.titel)}</h3><p class="uv-theme-line" style="margin:0">${esc(t.regel)}</p></div>`).join('\n');

// Schoon beginnen en vaste bestanden kopiëren
rmSync(uit, { recursive: true, force: true });
mkdirSync(uit, { recursive: true });
cpSync(join(hier, 'statisch'), uit, { recursive: true });

// Vandaag
const uit7 = data.boeken.find((b) => b.nummer === data.uitgelicht);
pagina({
  pad: '', titel: 'uitvloed — Nederlandse literatuur, opnieuw gedrukt', beschrijving: SLOGAN, actief: 'Vandaag',
  inhoud: (r) => `<div class="wrap">
  <section class="uv-hero">
    <a href="${r}reeks/${slug(uit7)}/">${kaftGroot(uit7)}</a>
    <div>
      <div class="uv-eyebrow uv-eyebrow-accent">Nu in pre-order · ${nr(uit7.nummer)}</div>
      <h1 class="uv-display">${esc(uit7.titel)}</h1>
      <div class="uv-author">${esc(uit7.auteur)}</div>
      ${uit7.onderregel ? `<p class="uv-lead">${esc(uit7.onderregel)}</p>` : ''}
      ${meter(uit7, r, false)}
      <div class="uv-actions">
        <a class="uv-btn" href="${r}reeks/${slug(uit7)}/">Pre-order · € 10</a>
        <a class="uv-btn uv-btn-secondary" href="${r}reeks/${slug(uit7)}/">Lees meer</a>
      </div>
    </div>
  </section>
  <section class="uv-section" aria-labelledby="verzamelen">
    <div class="uv-section-head"><h2 class="uv-eyebrow" id="verzamelen" style="margin:0">Nu aan het verzamelen</h2><a class="uv-textlink" href="${r}reeks/">de hele reeks →</a></div>
    <div class="uv-grid uv-grid-5">
${boeken.slice(0, 5).map((b) => item(b, r)).join('\n')}
    </div>
  </section>
  <section class="uv-section" aria-labelledby="verken">
    <div class="uv-section-head"><h2 class="uv-eyebrow" id="verken" style="margin:0">Verken de Nederlandse literatuur</h2></div>
    <p class="uv-section-sub">Toegankelijker dan het archief — begin bij een gevoel, niet bij een naam.</p>
    <div class="uv-themes">
${themaKaarten}
    </div>
  </section>
</div>`,
});

// De reeks
pagina({
  pad: 'reeks', titel: 'De reeks — uitvloed', beschrijving: 'Genummerd, om de tien euro, gedrukt op vraag.', actief: 'De reeks',
  inhoud: (r) => `<div class="wrap" style="padding-block: 48px 60px">
  <h1 class="uv-pagetitle">De reeks</h1>
  <p class="uv-sub">Genummerd, om de tien euro, gedrukt op vraag. Een kast die langzaam vol raakt.</p>
  <div class="uv-filter">
    <div class="uv-chips" role="group" aria-label="Toon boeken">
      <button type="button" class="uv-chip" data-filter="alles" aria-pressed="true">Alles · ${boeken.length}</button>
      ${FILTERS.map(([k, t]) => `<button type="button" class="uv-chip" data-filter="${k}" aria-pressed="false">${t}</button>`).join('\n      ')}
    </div>
    <div class="uv-sort">Sorteer op <b>nummer ↓</b></div>
  </div>
  <div class="uv-grid" id="catalogus">
${boeken.map((b) => item(b, r)).join('\n')}
  </div>
</div>
<script>
  document.querySelectorAll('[data-filter]').forEach(function (knop) {
    knop.addEventListener('click', function () {
      var f = knop.dataset.filter;
      document.querySelectorAll('[data-filter]').forEach(function (k) { k.setAttribute('aria-pressed', String(k === knop)); });
      document.querySelectorAll('#catalogus .uv-item').forEach(function (el) {
        el.hidden = f !== 'alles' && el.dataset.status !== f && !(f === 'verschenen' && el.dataset.status === 'uitverkocht');
      });
    });
  });
</script>`,
});

// Boekpagina's
for (const b of boeken) {
  pagina({
    pad: `reeks/${slug(b)}`, titel: `${b.titel} — uitvloed`, beschrijving: `${b.titel} door ${b.auteur}, ${nr(b.nummer)} in de reeks van uitvloed.`, actief: 'De reeks',
    inhoud: (r) => `<div class="wrap">
  <nav class="uv-crumbs" aria-label="Kruimelpad"><a href="${r}reeks/">De reeks</a><span aria-hidden="true">›</span><span>${nr(b.nummer)}</span><span aria-hidden="true">›</span><span aria-current="page">${esc(b.titel)}</span></nav>
  <div class="uv-book">
    <div class="uv-book-side">
      ${kaftGroot(b, true)}
      ${b.status === 'pre-order' ? meter(b, r, true) : `<div class="uv-card"><div class="uv-meter-goal" style="font-size:14px">${STATUS[b.status](b)}</div></div>`}
    </div>
    <div>
      <div class="uv-eyebrow uv-eyebrow-accent">${b.genre ? esc(b.genre) + ' · ' : ''}${nr(b.nummer)}</div>
      <h1 class="uv-title">${esc(b.titel)}</h1>
      <div class="uv-author">${esc(b.auteur)}</div>
      ${b.tekst ? `<div class="uv-body">${b.tekst.map((p) => `<p>${esc(p)}</p>`).join('')}</div>` : ''}
      ${b.status === 'pre-order' ? stappen : ''}
      ${b.gegevens ? `<dl class="uv-specs">${Object.entries(b.gegevens).map(([k, v]) => `<div><dt>${esc(k)}</dt><dd>${esc(v)}</dd></div>`).join('')}</dl>` : ''}
    </div>
  </div>
</div>`,
  });
}

// Verkennen
pagina({
  pad: 'verkennen', titel: 'Verkennen — uitvloed', beschrijving: 'Verken de Nederlandse literatuur.', actief: 'Verkennen',
  inhoud: () => `<div class="wrap" style="padding-block: 48px 60px">
  <h1 class="uv-pagetitle">Verkennen</h1>
  <p class="uv-sub">Toegankelijker dan het archief — begin bij een gevoel, niet bij een naam.</p>
  <div class="uv-themes">
${themaKaarten}
  </div>
</div>`,
});

// Over uitvloed
pagina({
  pad: 'over', titel: 'Over uitvloed', beschrijving: SLOGAN, actief: 'Over uitvloed',
  inhoud: (r) => `<div class="wrap" style="padding-block: 48px 60px">
  <h1 class="uv-pagetitle">Over uitvloed</h1>
  <p class="uv-sub">${SLOGAN}</p>
  <div class="uv-body">
    <p>uitvloed drukt Nederlandse literatuur opnieuw, maar pas als genoeg lezers erom vragen. Elk boek krijgt een nummer in één doorlopende reeks, kost € 10 en verschijnt als pocket op warm crème papier.</p>
    <p>Zo blijft er geen stapel onverkochte boeken achter: we drukken nooit meer dan nodig.</p>
  </div>
  ${stappen}
  <a class="uv-textlink" href="${r}reeks/">bekijk de reeks →</a>
</div>`,
});

// Mijn account (inloggen met een link per e-mail)
pagina({
  pad: 'account', titel: 'Mijn account — uitvloed', beschrijving: 'Log in bij uitvloed.', actief: '',
  inhoud: (r) => `<div class="wrap uv-account" style="padding-block: 48px 60px">
  <h1 class="uv-pagetitle">Mijn account</h1>
  <p class="uv-sub" data-staat="laden">Even kijken of je al bent ingelogd…</p>
  <section data-staat="uit" hidden>
    <p class="uv-sub">Log in met je e-mailadres. Je krijgt een link waarmee je direct binnen bent, zonder wachtwoord.</p>
    <form class="uv-card uv-form" id="inlogformulier" novalidate>
      <label for="email">E-mailadres</label>
      <input class="uv-field" id="email" name="email" type="email" autocomplete="email" required placeholder="jij@voorbeeld.nl">
      <button class="uv-btn uv-btn-block" type="submit">Stuur mij een inloglink</button>
      <p class="uv-melding" data-melding="inloggen" role="status"></p>
    </form>
  </section>
  <section data-staat="verstuurd" hidden>
    <div class="uv-card uv-form">
      <div class="uv-eyebrow uv-eyebrow-accent">Kijk in je mail</div>
      <p class="uv-body" style="margin: 12px 0 0">We hebben een inloglink gestuurd naar <b data-email></b>. Klik op de link in de mail om in te loggen. De link werkt één keer en vervalt na 15 minuten.</p>
    </div>
  </section>
  <section data-staat="in" hidden>
    <p class="uv-sub">Ingelogd als <b data-email></b>.</p>
    <div class="uv-section-head"><h2 class="uv-eyebrow" style="margin:0">Mijn pre-orders</h2><a class="uv-textlink" href="${r}reeks/">de hele reeks →</a></div>
    <ul class="uv-list" data-lijst></ul>
    <p class="uv-lead" data-leeg hidden>Je hebt nog geen boeken gereserveerd.</p>
    <button type="button" class="uv-btn uv-btn-secondary" data-uitloggen>Uitloggen</button>
  </section>
</div>`,
});

// Pagina voor adressen die niet bestaan
pagina({
  pad: '', bestand: '404.html', titel: 'Niet gevonden — uitvloed', beschrijving: 'Deze pagina bestaat niet.', actief: '',
  inhoud: () => `<div class="wrap" style="padding-block: 48px 60px">
  <h1 class="uv-pagetitle">Deze pagina bestaat niet</h1>
  <p class="uv-sub">Misschien is het boek verhuisd naar een ander nummer.</p>
  <a class="uv-textlink" href="/reeks/">naar de reeks →</a>
</div>`,
});

console.log(`Gebouwd: ${boeken.length} boeken, ${boeken.length + 5} pagina's → ${uit}`);
