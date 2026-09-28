// Leest de reeks van uitvloed: instellingen uit reeks.json en één bestand per boek uit boeken/.
// Gebruikt door de site (src/_data/reeks.mjs) en door de server.
import { readFileSync, readdirSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

const HIER = fileURLToPath(new URL('.', import.meta.url));
const VERPLICHT = ['nummer', 'titel', 'auteur', 'jaar', 'kort', 'status', 'kleur'];
const STATUSSEN = ['pre-order', 'verschenen', 'binnenkort', 'uitverkocht'];

// /reeks/07-de-stille-kade/
export const boekSlug = (b) => String(b.nummer).padStart(2, '0') + '-' + b.titel.toLowerCase()
  .normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
export const boekPad = (b) => `/reeks/${boekSlug(b)}/`;

export function laadReeks(map = HIER) {
  const reeks = JSON.parse(readFileSync(join(map, 'reeks.json'), 'utf8'));
  const boekenMap = join(map, 'boeken');
  const boeken = readdirSync(boekenMap).filter((f) => f.endsWith('.json')).map((f) => {
    const b = JSON.parse(readFileSync(join(boekenMap, f), 'utf8'));
    const mist = VERPLICHT.filter((v) => b[v] === undefined || b[v] === '');
    if (mist.length) throw new Error(`boeken/${f}: ${mist.join(', ')} ontbreekt.`);
    if (!STATUSSEN.includes(b.status)) throw new Error(`boeken/${f}: status moet een van ${STATUSSEN.join(', ')} zijn.`);
    return { ...b, slug: boekSlug(b), pad: boekPad(b) };
  }).sort((a, b) => b.nummer - a.nummer);

  const dubbel = boeken.find((b, i) => boeken.findIndex((c) => c.nummer === b.nummer) !== i);
  if (dubbel) throw new Error(`Nummer ${dubbel.nummer} komt twee keer voor in boeken/.`);
  if (reeks.uitgelicht !== undefined && !boeken.some((b) => b.nummer === reeks.uitgelicht)) {
    throw new Error(`reeks.json: uitgelicht boek ${reeks.uitgelicht} staat niet in boeken/.`);
  }
  return { ...reeks, boeken };
}
