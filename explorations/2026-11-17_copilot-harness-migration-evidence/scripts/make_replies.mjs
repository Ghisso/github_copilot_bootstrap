// Create scripted hook replies for one run. Usage: node make_replies.mjs <run-name> <spec.json>
import fs from "node:fs";
import path from "node:path";

const [, , run, specFile] = process.argv;
const here = path.dirname(new URL(import.meta.url).pathname);
const dir = path.join(here, "replies", run);
fs.rmSync(dir, { recursive: true, force: true });
fs.mkdirSync(dir, { recursive: true });
const spec = JSON.parse(fs.readFileSync(specFile, "utf8"));
for (const entry of spec) {
    const base = path.join(dir, `${entry.tag}.${entry.label}`);
    if (entry.reply !== undefined) fs.writeFileSync(base + ".reply", typeof entry.reply === "string" ? entry.reply : JSON.stringify(entry.reply));
    if (entry.stderr !== undefined) fs.writeFileSync(base + ".stderr", entry.stderr);
    if (entry.exit !== undefined) fs.writeFileSync(base + ".exit", String(entry.exit));
    if (entry.sleep !== undefined) fs.writeFileSync(base + ".sleep", String(entry.sleep));
    if (entry.unless !== undefined) fs.writeFileSync(base + ".unless", entry.unless);
}
console.log(`replies for ${run}: ${spec.length} entries`);
