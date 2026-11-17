// Enable or disable hook sources in a probe project copy.
// Usage: node toggle_sources.mjs <project> <both|copilot-only|claude-only|probe-only>
// "probe-only" disables both bootstrap hook sources and keeps the probe loggers.
import fs from "node:fs";
import path from "node:path";

const [, , project, mode] = process.argv;
const copilot = path.join(project, ".github", "hooks", "hooks.json");
const claude = path.join(project, ".claude", "settings.json");
const set = (file, enabled) => {
    const off = file + ".off";
    if (enabled && fs.existsSync(off)) fs.renameSync(off, file);
    if (!enabled && fs.existsSync(file)) fs.renameSync(file, off);
};
set(copilot, mode === "both" || mode === "copilot-only");
set(claude, mode === "both" || mode === "claude-only");
console.log(`sources mode=${mode}: copilot hook file ${fs.existsSync(copilot) ? "on" : "off"}, claude settings ${fs.existsSync(claude) ? "on" : "off"}`);
