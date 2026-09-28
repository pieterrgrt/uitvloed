// Maakt een consistente kopie van de database, ook terwijl de server draait.
// Gebruik (op de server): docker compose exec web node server/src/backup.mjs
import { DatabaseSync } from 'node:sqlite';
import { mkdirSync } from 'node:fs';
import { dirname, join } from 'node:path';

const bron = process.env.UV_DATABASE ?? '/data/uitvloed.db';
const map = join(dirname(bron), 'backups');
const doel = join(map, `uitvloed-${new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-')}.db`);
mkdirSync(map, { recursive: true });
const db = new DatabaseSync(bron);
db.exec(`VACUUM INTO '${doel.replaceAll("'", "''")}'`);
db.close();
console.log(doel);
