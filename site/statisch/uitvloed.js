// uitvloed — inloggen, pre-orders en live vraagmeters. De pagina's werken ook zonder dit script.
(function () {
  'use strict';
  var $ = function (sel, el) { return (el || document).querySelector(sel); };
  var $$ = function (sel, el) { return Array.prototype.slice.call((el || document).querySelectorAll(sel)); };

  function api(pad, methode, body) {
    return fetch(pad, {
      method: methode || 'GET',
      credentials: 'same-origin',
      headers: body ? { 'Content-Type': 'application/json' } : {},
      body: body ? JSON.stringify(body) : undefined,
    }).then(function (r) {
      return r.json().catch(function () { return {}; }).then(function (d) {
        if (!r.ok) { var e = new Error(d.fout || 'Er ging iets mis. Probeer het later opnieuw.'); e.status = r.status; throw e; }
        return d;
      });
    });
  }

  function melding(sleutel, tekst, fout) {
    var el = $('[data-melding="' + sleutel + '"]');
    if (!el) return;
    el.textContent = tekst || '';
    el.classList.toggle('is-fout', !!fout);
  }

  var accountLink = $('[data-account]');
  var accountPad = accountLink ? accountLink.getAttribute('href') : '/account/';

  // Wie is er ingelogd? null = niet ingelogd, false = server niet bereikbaar.
  var ik = api('/api/ik').catch(function (e) { return e.status === 401 ? null : false; });

  ik.then(function (g) {
    if (g && accountLink) accountLink.textContent = 'Mijn account';
  });

  // Vraagmeters bijwerken met het actuele aantal.
  function zetTeller(nummer, aantal) {
    $$('[data-teller="' + nummer + '"]').forEach(function (m) {
      var doel = Number(m.dataset.doel) || 500;
      var nog = Math.max(0, doel - aantal);
      $('[data-aantal]', m).textContent = aantal;
      $('[data-vulling]', m).style.width = Math.min(100, Math.round((aantal / doel) * 100)) + '%';
      $('[data-balk]', m).setAttribute('aria-valuenow', aantal);
      $('[data-notitie]', m).textContent = nog ? 'Nog ' + nog + ' lezers en de persen draaien.' : 'Het doel is gehaald. De persen draaien.';
    });
  }
  if ($('[data-teller]')) {
    api('/api/tellers').then(function (t) { Object.keys(t).forEach(function (n) { zetTeller(n, t[n]); }); }).catch(function () {});
  }

  // Pre-orderknoppen op de boekpagina.
  function toonGeplaatst(nummer, geplaatst) {
    var knop = $('[data-preorder="' + nummer + '"]');
    var annuleer = $('[data-annuleer="' + nummer + '"]');
    if (!knop || !annuleer) return;
    knop.hidden = geplaatst;
    annuleer.hidden = !geplaatst;
    melding(nummer, geplaatst ? 'Je exemplaar is gereserveerd. Je vindt het terug onder Mijn account.' : '');
  }
  $$('[data-preorder]').forEach(function (knop) {
    var nummer = Number(knop.dataset.preorder);
    ik.then(function (g) {
      if (g && g.preorders.some(function (p) { return p.nummer === nummer; })) toonGeplaatst(nummer, true);
    });
    knop.addEventListener('click', function () {
      ik.then(function (g) {
        if (g === false) return melding(nummer, 'Bestellen lukt op dit moment niet. Probeer het later opnieuw.', true);
        if (!g) { location.href = accountPad + '?terug=' + encodeURIComponent(location.pathname); return; }
        knop.disabled = true;
        api('/api/preorders', 'POST', { nummer: nummer })
          .then(function (d) { zetTeller(nummer, d.teller); toonGeplaatst(nummer, true); })
          .catch(function (e) { melding(nummer, e.message, true); })
          .then(function () { knop.disabled = false; });
      });
    });
  });
  $$('[data-annuleer]').forEach(function (knop) {
    var nummer = Number(knop.dataset.annuleer);
    knop.addEventListener('click', function () {
      knop.disabled = true;
      api('/api/preorders', 'DELETE', { nummer: nummer })
        .then(function (d) { zetTeller(nummer, d.teller); toonGeplaatst(nummer, false); melding(nummer, 'Je pre-order is geannuleerd.'); })
        .catch(function (e) { melding(nummer, e.message, true); })
        .then(function () { knop.disabled = false; });
    });
  });

  // Accountpagina.
  var account = $('.uv-account');
  if (!account) return;
  var params = new URLSearchParams(location.search);
  var terug = params.get('terug') || '';

  function toon(staat) {
    $$('[data-staat]', account).forEach(function (s) { s.hidden = s.dataset.staat !== staat; });
  }
  function toonIngelogd(g) {
    $$('[data-email]', account).forEach(function (el) { el.textContent = g.email; });
    var lijst = $('[data-lijst]', account);
    lijst.textContent = '';
    g.preorders.forEach(function (p) {
      var li = document.createElement('li');
      var a = document.createElement('a');
      a.textContent = p.titel;
      a.href = p.pad || '/reeks/';
      var s = document.createElement('span');
      s.textContent = '№ ' + String(p.nummer).padStart(2, '0') + ' · ' + p.auteur;
      li.appendChild(a); li.appendChild(s); lijst.appendChild(li);
    });
    $('[data-leeg]', account).hidden = g.preorders.length > 0;
    if (accountLink) accountLink.textContent = 'Mijn account';
    toon('in');
  }

  var token = params.get('token');
  if (token) {
    history.replaceState(null, '', location.pathname);
    api('/api/inloggen/bevestig', 'POST', { token: token })
      .then(function (d) {
        if (d.terug && d.terug !== location.pathname) { location.replace(d.terug); return; }
        return api('/api/ik').then(toonIngelogd);
      })
      .catch(function (e) { toon('uit'); melding('inloggen', e.message, true); });
  } else {
    ik.then(function (g) {
      if (g) return toonIngelogd(g);
      toon('uit');
      if (g === false) melding('inloggen', 'Inloggen lukt op dit moment niet. Probeer het later opnieuw.', true);
    });
  }

  $('#inlogformulier').addEventListener('submit', function (ev) {
    ev.preventDefault();
    var email = $('#email').value.trim();
    if (!email) return melding('inloggen', 'Vul je e-mailadres in.', true);
    var knop = $('button[type="submit"]', ev.target);
    knop.disabled = true;
    melding('inloggen', '');
    api('/api/inloggen', 'POST', { email: email, terug: terug })
      .then(function () {
        $$('[data-email]', account).forEach(function (el) { el.textContent = email; });
        toon('verstuurd');
      })
      .catch(function (e) { melding('inloggen', e.message, true); })
      .then(function () { knop.disabled = false; });
  });

  $('[data-uitloggen]', account).addEventListener('click', function () {
    api('/api/uitloggen', 'POST', {}).then(function () {
      if (accountLink) accountLink.textContent = 'Aanmelden';
      toon('uit');
      melding('inloggen', 'Je bent uitgelogd.');
    });
  });
})();
