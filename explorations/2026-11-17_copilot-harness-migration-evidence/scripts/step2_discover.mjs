// Spike step 2: ask the bundled Copilot runtime what it would load from a project
// (hooks, MCP servers, instructions, skills, agents). No account, no model call.
import { pathToFileURL } from "node:url";
import path from "node:path";
import fs from "node:fs";

const [, , sdkRoot, copilotHome, project, outFile] = process.argv;
const sdk = await import(pathToFileURL(path.join(sdkRoot, "dist", "index.js")).href);

const client = new sdk.CopilotClient({
    baseDirectory: copilotHome,
    useLoggedInUser: false,
    logLevel: "error",
    workingDirectory: project,
});
const result = {};
const call = async (name, fn) => {
    try {
        result[name] = await fn();
    } catch (error) {
        result[name] = { __error: String(error && error.message ? error.message : error) };
    }
};
try {
    await client.start();
    result.status = await client.getStatus();
    const rpc = client.rpc;
    const projectPaths = [project];
    await call("hooks.discover", () => rpc.hooks.discover({ projectPaths }));
    await call("mcp.discover", () => rpc.mcp.discover({ workingDirectory: project, includeEffectiveSource: true }));
    await call("instructions.getDiscoveryPaths", () => rpc.instructions.getDiscoveryPaths({ projectPaths }));
    await call("instructions.discover", () => rpc.instructions.discover({ projectPaths }));
    await call("skills.getDiscoveryPaths", () => rpc.skills.getDiscoveryPaths({ projectPaths }));
    await call("skills.discover", () => rpc.skills.discover({ projectPaths }));
    await call("agents.getDiscoveryPaths", () => rpc.agents.getDiscoveryPaths({ projectPaths }));
    await call("agents.discover", () => rpc.agents.discover({ projectPaths }));
    await call("tools.list", () => rpc.tools.list({}));
    await call("user.settings.get", () => rpc.user.settings.get({}));
} finally {
    await client.stop();
}
fs.writeFileSync(outFile, JSON.stringify(result, null, 2));
const strip = (s) => (typeof s === "string" ? s.split(project).join("<project>").split(copilotHome).join("<home>") : s);
const summarize = (name) => {
    const value = result[name];
    if (!value) return;
    if (value.__error) return console.log(`${name}: ERROR ${strip(value.__error)}`);
    for (const [key, entry] of Object.entries(value)) {
        if (Array.isArray(entry)) console.log(`${name}.${key}: ${entry.length} item(s)`);
        else console.log(`${name}.${key}: ${strip(JSON.stringify(entry)).slice(0, 300)}`);
    }
};
for (const name of Object.keys(result)) summarize(name);
