// Database van uitvloed: gebruikers, inloglinks, sessies en pre-orders (SQLite, ingebouwd in Node).
import { DatabaseSync } from 'node:sqlite';
import { mkdirSync } from 'node:fs';
import { dirname } from 'node:path';

export function openDatabase(pad) {
  if (pad !== ':memory:') mkdirSync(dirname(pad), { recursive: true });
  const db = new DatabaseSync(pad);
  db.exec(`
    PRAGMA journal_mode = WAL;
    PRAGMA foreign_keys = ON;
    CREATE TABLE IF NOT EXISTS gebruikers (
      id        INTEGER PRIMARY KEY,
      email     TEXT NOT NULL UNIQUE,
      aangemaakt TEXT NOT NULL DEFAULT (datetime('now'))
    );
    CREATE TABLE IF NOT EXISTS inloglinks (
      hash      TEXT PRIMARY KEY,
      email     TEXT NOT NULL,
      terug     TEXT NOT NULL,
      verloopt  INTEGER NOT NULL
    );
    CREATE TABLE IF NOT EXISTS sessies (
      hash      TEXT PRIMARY KEY,
      gebruiker INTEGER NOT NULL REFERENCES gebruikers(id) ON DELETE CASCADE,
      verloopt  INTEGER NOT NULL
    );
    CREATE TABLE IF NOT EXISTS preorders (
      gebruiker INTEGER NOT NULL REFERENCES gebruikers(id) ON DELETE CASCADE,
      boek      INTEGER NOT NULL,
      geplaatst TEXT NOT NULL DEFAULT (datetime('now')),
      PRIMARY KEY (gebruiker, boek)
    );
  `);

  const q = {
    linkOpslaan: db.prepare('INSERT INTO inloglinks (hash, email, terug, verloopt) VALUES (?, ?, ?, ?)'),
    linkPakken: db.prepare('DELETE FROM inloglinks WHERE hash = ? RETURNING email, terug, verloopt'),
    gebruikerZoeken: db.prepare('SELECT id, email FROM gebruikers WHERE email = ?'),
    gebruikerMaken: db.prepare('INSERT INTO gebruikers (email) VALUES (?) RETURNING id, email'),
    sessieOpslaan: db.prepare('INSERT INTO sessies (hash, gebruiker, verloopt) VALUES (?, ?, ?)'),
    sessieZoeken: db.prepare(`SELECT g.id, g.email FROM sessies s JOIN gebruikers g ON g.id = s.gebruiker
                              WHERE s.hash = ? AND s.verloopt > ?`),
    sessieWissen: db.prepare('DELETE FROM sessies WHERE hash = ?'),
    preorderPlaatsen: db.prepare('INSERT OR IGNORE INTO preorders (gebruiker, boek) VALUES (?, ?)'),
    preorderAnnuleren: db.prepare('DELETE FROM preorders WHERE gebruiker = ? AND boek = ?'),
    preordersVan: db.prepare('SELECT boek, geplaatst FROM preorders WHERE gebruiker = ? ORDER BY geplaatst'),
    tellers: db.prepare('SELECT boek, COUNT(*) AS aantal FROM preorders GROUP BY boek'),
    opruimen: db.prepare('DELETE FROM inloglinks WHERE verloopt <= ?'),
    sessiesOpruimen: db.prepare('DELETE FROM sessies WHERE verloopt <= ?'),
  };

  return {
    linkOpslaan: (hash, email, terug, verloopt) => q.linkOpslaan.run(hash, email, terug, verloopt),
    linkPakken: (hash) => q.linkPakken.get(hash),
    gebruikerVoor(email) {
      return q.gebruikerZoeken.get(email) ?? q.gebruikerMaken.get(email);
    },
    sessieOpslaan: (hash, gebruiker, verloopt) => q.sessieOpslaan.run(hash, gebruiker, verloopt),
    sessieZoeken: (hash) => q.sessieZoeken.get(hash, Date.now()),
    sessieWissen: (hash) => q.sessieWissen.run(hash),
    preorderPlaatsen: (gebruiker, boek) => q.preorderPlaatsen.run(gebruiker, boek).changes === 1,
    preorderAnnuleren: (gebruiker, boek) => q.preorderAnnuleren.run(gebruiker, boek).changes === 1,
    preordersVan: (gebruiker) => q.preordersVan.all(gebruiker),
    tellers: () => Object.fromEntries(q.tellers.all().map((r) => [r.boek, r.aantal])),
    opruimen() {
      const nu = Date.now();
      q.opruimen.run(nu);
      q.sessiesOpruimen.run(nu);
    },
    sluiten: () => db.close(),
  };
}
