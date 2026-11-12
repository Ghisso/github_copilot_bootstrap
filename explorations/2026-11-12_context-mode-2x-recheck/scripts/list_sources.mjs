// Print the sources table of a Context Mode 2.x context.db (read-only): node list_sources.mjs <db>
import { DatabaseSync } from "node:sqlite";
const db = new DatabaseSync(process.argv[2], { readOnly: true });
for (const r of db.prepare("SELECT * FROM sources").all()) console.log(r.id, r.kind ?? r.source_kind, r.label);
